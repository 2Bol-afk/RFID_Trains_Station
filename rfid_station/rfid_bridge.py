#!/usr/bin/env python3
"""
RFID Bridge Script for RFID Card Payment System

This script reads UID from RFID readers and posts ride charges to the Django API.
Supports both serial/USB readers and keyboard emulator readers.

Usage:
    python rfid_bridge.py --serial /dev/ttyUSB0
    python rfid_bridge.py --keyboard
    python rfid_bridge.py --test

Requirements:
    pip install pyserial requests
"""

import argparse
import sys
import time
import json
import logging
import threading
from typing import Optional, Callable
import requests
from datetime import datetime

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not available. Serial reader support disabled.")

# Keyboard emulator mode removed for production


class RfidBridge:
    """Main RFID bridge class for handling reader input and API communication."""
    
    def __init__(self, api_base_url: str, bridge_token: str, ride_cost: float = 20.0):
        """
        Initialize the RFID bridge.
        
        Args:
            api_base_url: Base URL of the Django API
            bridge_token: Authentication token for the bridge
            ride_cost: Cost per ride in pesos
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.bridge_token = bridge_token
        self.ride_cost = ride_cost
        self.session = requests.Session()
        self.session.headers.update({
            'X-BRIDGE-TOKEN': bridge_token,
            'Content-Type': 'application/json'
        })
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('rfid_bridge.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Statistics removed for production
    
    def post_ride_charge(self, uid: str) -> bool:
        """
        Post a ride charge to the API.
        
        Args:
            uid: RFID card UID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            url = f"{self.api_base_url}/api/cards/{uid}/ride/"
            response = self.session.post(url, json={}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Ride charged successfully for {uid}. New balance: ₱{data.get('balance', 'N/A')}")
                return True
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', f'HTTP {response.status_code}')
                self.logger.error(f"Failed to charge ride for {uid}: {error_msg}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error charging ride for {uid}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error charging ride for {uid}: {e}")
            return False
    
    def get_card_balance(self, uid: str) -> Optional[dict]:
        """
        Get card balance information.
        
        Args:
            uid: RFID card UID
            
        Returns:
            dict: Card information or None if failed
        """
        try:
            url = f"{self.api_base_url}/api/cards/{uid}/balance/"
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Failed to get balance for {uid}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting balance for {uid}: {e}")
            return None
    
    def process_uid(self, uid: str) -> None:
        """
        Process a scanned UID.
        
        Args:
            uid: RFID card UID
        """
        uid = uid.strip()
        if not uid:
            return
        
        self.logger.info(f"Processing UID: {uid}")
        
        # Get card balance first
        card_info = self.get_card_balance(uid)
        if card_info:
            balance = card_info.get('balance', 'N/A')
            status = card_info.get('status', 'Unknown')
            can_be_used = card_info.get('can_be_used', False)
            
            self.logger.info(f"Card {uid}: Status={status}, Balance=₱{balance}, Can be used={can_be_used}")
            
            if not can_be_used:
                self.logger.warning(f"Card {uid} cannot be used (insufficient balance or inactive)")
                self.stats['failed_rides'] += 1
                return
        
        # Attempt to charge the ride
        success = self.post_ride_charge(uid)
        
        # Optional: hook success/failure feedback via GPIO/buzzer here
    
    def run_serial_reader(self, port: str, baudrate: int = 9600) -> None:
        """
        Run with serial/USB RFID reader.
        
        Args:
            port: Serial port (e.g., '/dev/ttyUSB0' or 'COM3')
            baudrate: Baud rate for serial communication
        """
        if not SERIAL_AVAILABLE:
            self.logger.error("Serial support not available. Install pyserial: pip install pyserial")
            return
        
        self.logger.info(f"Starting serial reader on {port} at {baudrate} baud")
        
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            self.logger.info(f"Serial connection established on {port}")
            
            while True:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.process_uid(line)
                except serial.SerialException as e:
                    self.logger.error(f"Serial error: {e}")
                    time.sleep(1)
                except KeyboardInterrupt:
                    break
                    
        except serial.SerialException as e:
            self.logger.error(f"Failed to open serial port {port}: {e}")
        finally:
            if 'ser' in locals():
                ser.close()
                self.logger.info("Serial connection closed")
    
    # Test and keyboard modes removed for production


def main():
    """Main function to run the RFID bridge."""
    parser = argparse.ArgumentParser(description='RFID Bridge for Card Payment System')
    parser.add_argument('--api-url', default='http://localhost:8000',
                       help='Django API base URL (default: http://localhost:8000)')
    parser.add_argument('--token', default='rfid-bridge-secret-token-2024',
                       help='Bridge authentication token')
    parser.add_argument('--ride-cost', type=float, default=20.0,
                       help='Ride cost in pesos (default: 20.0)')
    
    # Reader options
    parser.add_argument('--serial', metavar='PORT', required=True,
                       help='Use serial reader (e.g., /dev/ttyUSB0 or COM3)')
    
    # Serial options
    parser.add_argument('--baudrate', type=int, default=9600,
                       help='Serial baud rate (default: 9600)')
    
    args = parser.parse_args()
    
    # Create bridge instance
    bridge = RfidBridge(
        api_base_url=args.api_url,
        bridge_token=args.token,
        ride_cost=args.ride_cost
    )
    
    try:
        bridge.run_serial_reader(args.serial, args.baudrate)
    except KeyboardInterrupt:
        print("\nShutting down RFID bridge...")
    finally:
        pass


if __name__ == '__main__':
    main()

