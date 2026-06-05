"""
ui/dashboard.py - Flask web dashboard for trading bot
Real-time monitoring and manual control
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
from typing import Dict
import json
from utils.trade_queue import command_queue, add_exit_command
from config.logger import logger

# Global app state (shared with main bot)
app_state = {
    "account": {},
    "positions": [],
    "recent_trades": [],
    "performance": {},
    "status": "IDLE",
}

def create_app():
    """Create Flask app instance."""
    
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False
    
    # =========================================================================
    # DASHBOARD ROUTES
    # =========================================================================
    
    @app.route("/")
    def dashboard():
        """Main dashboard page."""
        return render_template("index.html")
    
    # =========================================================================
    # API ROUTES - DATA
    # =========================================================================
    
    @app.route("/api/status", methods=["GET"])
    def get_status():
        """Get bot status."""
        
        return jsonify({
            "status": app_state.get("status"),
            "timestamp": datetime.now().isoformat(),
            "trading_active": app_state.get("status") == "RUNNING",
        })
    
    @app.route("/api/account", methods=["GET"])
    def get_account():
        """Get account information."""
        
        return jsonify(app_state.get("account", {}))
    
    @app.route("/api/positions", methods=["GET"])
    def get_positions():
        """Get open positions."""
        
        positions = app_state.get("positions", [])
        
        return jsonify({
            "open_positions": positions,
            "total_positions": len(positions),
            "total_unrealized_pl": sum([p.get("unrealized_pl", 0) for p in positions]),
            "total_unrealized_pl_pct": sum([p.get("unrealized_pl_pct", 0) for p in positions]) / len(positions) if positions else 0,
        })
    
    @app.route("/api/trades", methods=["GET"])
    def get_recent_trades():
        """Get recent trades."""
        
        limit = request.args.get("limit", 50, type=int)
        trades = app_state.get("recent_trades", [])[-limit:]
        
        return jsonify({
            "recent_trades": trades,
            "total_count": len(trades),
        })
    
    @app.route("/api/performance", methods=["GET"])
    def get_performance():
        """Get performance metrics."""
        
        return jsonify(app_state.get("performance", {}))
    
    # =========================================================================
    # API ROUTES - ACTIONS
    # =========================================================================
    
    @app.route("/api/trade/exit", methods=["POST"])
    def exit_trade():
        """
        Manually exit a trade.
        NOW ACTUALLY EXECUTES!
        """
        
        try:
            data = request.json or {}
            symbol = data.get("symbol")
            portion = float(data.get("portion", "all"))
            
            if not symbol:
                return jsonify({"error": "Symbol required"}), 400
            
            # Convert portion string to fraction
            if portion == "all":
                portion = 1.0
            elif portion == "half":
                portion = 0.5
            else:
                try:
                    portion = float(portion) / 100  # Convert % to decimal
                except:
                    portion = 1.0
            
            # ✅ ADD TO COMMAND QUEUE
            if add_exit_command(symbol, portion):
                logger.info(f"Exit command queued: {symbol} ({portion*100:.0f}%)")
                
                return jsonify({
                    "success": True,
                    "message": f"Exit order queued for {symbol} ({portion*100:.0f}%)",
                    "symbol": symbol,
                    "portion": portion,
                    "timestamp": datetime.now().isoformat(),
                }), 202  # 202 Accepted
            else:
                return jsonify({
                    "error": "Queue full - try again later"
                }), 503
        
        except Exception as e:
            logger.error(f"Error queuing exit: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/trade/cancel", methods=["POST"])
    def cancel_order():
        """Cancel a pending order."""
        
        try:
            data = request.json or {}
            order_id = data.get("order_id")
            
            if not order_id:
                return jsonify({"error": "Order ID required"}), 400
            
            # ✅ ADD TO COMMAND QUEUE
            command = TradeCommand(
                command_type="CANCEL",
                order_id=order_id
            )
            
            if command_queue.put_command(command):
                logger.info(f"Cancel command queued: {order_id}")
                
                return jsonify({
                    "success": True,
                    "message": f"Cancel order queued: {order_id}",
                    "order_id": order_id,
                }), 202
            else:
                return jsonify({"error": "Queue full"}), 503
        
        except Exception as e:
            logger.error(f"Error queuing cancel: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/bot/pause", methods=["POST"])
    def pause_bot():
        """Pause the bot."""
        
        try:
            command = TradeCommand(command_type="PAUSE")
            
            if command_queue.put_command(command):
                app_state["status"] = "PAUSED"
                logger.info("Pause command queued")
                
                return jsonify({
                    "success": True,
                    "message": "Bot pause command queued",
                    "status": "PAUSED",
                }), 202
            else:
                return jsonify({"error": "Queue full"}), 503
        
        except Exception as e:
            logger.error(f"Error pausing bot: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/bot/resume", methods=["POST"])
    def resume_bot():
        """Resume the bot."""
        
        try:
            command = TradeCommand(command_type="RESUME")
            
            if command_queue.put_command(command):
                app_state["status"] = "RUNNING"
                logger.info("Resume command queued")
                
                return jsonify({
                    "success": True,
                    "message": "Bot resume command queued",
                    "status": "RUNNING",
                }), 202
            else:
                return jsonify({"error": "Queue full"}), 503
        
        except Exception as e:
            logger.error(f"Error resuming bot: {e}")
            return jsonify({"error": str(e)}), 500
    
    # =========================================================================
    # ERROR HANDLERS
    # =========================================================================
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    return app

def update_app_state(new_state: Dict):
    """Update app state (called from main bot)."""
    
    global app_state
    app_state.update(new_state)