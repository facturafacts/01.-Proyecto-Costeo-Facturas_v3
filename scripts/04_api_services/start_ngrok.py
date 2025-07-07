#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Start Ngrok Tunnel for CFDI Processing System v4

Creates a public tunnel to the local FastAPI server for Google Sheets access.
"""

import sys
import logging
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyngrok import ngrok, conf
from config.settings import get_settings

def main():
    """Start ngrok tunnel to the FastAPI server."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Get settings
    settings = get_settings()
    
    logger.info("🌐 Starting Ngrok Tunnel for CFDI API")
    logger.info("=" * 50)
    
    try:
        # Configure ngrok
        if settings.NGROK_AUTH_TOKEN:
            logger.info("🔑 Setting ngrok auth token...")
            ngrok.set_auth_token(settings.NGROK_AUTH_TOKEN)
        else:
            logger.warning("⚠️ No NGROK_AUTH_TOKEN found in environment variables")
            logger.info("💡 You can set it with: export NGROK_AUTH_TOKEN=your_token")
        
        # Create tunnel configuration
        tunnel_config = {
            "bind_tls": True,  # Use HTTPS
            "inspect": True,   # Enable ngrok web interface
        }
        
        # Add custom domain if configured
        if settings.NGROK_DOMAIN:
            tunnel_config["hostname"] = settings.NGROK_DOMAIN
            logger.info(f"🏷️ Using custom domain: {settings.NGROK_DOMAIN}")
        
        # Create tunnel to local API server
        api_url = f"{settings.API_HOST}:{settings.API_PORT}"
        logger.info(f"🔗 Creating tunnel to: {api_url}")
        
        # Start tunnel
        public_tunnel = ngrok.connect(
            addr=api_url,
            **tunnel_config
        )
        
        # Get public URL
        public_url = public_tunnel.public_url
        
        logger.info("=" * 50)
        logger.info("✅ Ngrok tunnel created successfully!")
        logger.info(f"🌐 Public URL: {public_url}")
        logger.info(f"📊 API Endpoint: {public_url}/api/invoices/metadata")
        logger.info(f"📖 API Docs: {public_url}/docs")
        logger.info(f"🔍 Health Check: {public_url}/api/health")
        logger.info("=" * 50)
        logger.info("📝 For Google Apps Script, use this URL:")
        logger.info(f"   const API_URL = '{public_url}/api/invoices/metadata';")
        logger.info("=" * 50)
        logger.info("📊 Ngrok Web Interface: http://127.0.0.1:4040")
        logger.info("Press Ctrl+C to stop the tunnel")
        
        # Keep tunnel alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n🛑 Stopping ngrok tunnel...")
            ngrok.disconnect(public_tunnel.public_url)
            ngrok.kill()
            logger.info("✅ Ngrok tunnel stopped")
            
    except Exception as e:
        logger.error(f"❌ Failed to start ngrok tunnel: {e}")
        logger.error("💡 Make sure:")
        logger.error("   1. Your API server is running on the configured port")
        logger.error("   2. You have a valid ngrok auth token")
        logger.error("   3. Ngrok is installed and accessible")
        sys.exit(1)

if __name__ == "__main__":
    main() 