import socket
import sys
import struct
import time
import os
from datetime import datetime

SKY_BLUE = "\033[96m"
PURE_RED = "\033[31m"  # Pure standard red color
RESET = "\033[0m"

def print_noctraptor_banner():
    """Prints the high-density block NOCTRAPTOR banner with a top-to-bottom animation delay."""
    banner = [
        "███╗   ██╗ ██████╗  ██████╗████████╗██████╗  █████╗ ██████╗ ████████╗ ██████╗ ██████╗ ",
        "████╗  ██║██╔═══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗",
        "██╔██╗ ██║██║   ██║██║        ██║   ██████╔╝███████║██████╔╝   ██║   ██║   ██║██████╔╝",
        "██║╚██╗██║██║   ██║██║        ██║   ██╔══██╗██╔══██║██╔═══╝    ██║   ██║   ██║██╔══██╗",
        "██║ ╚████║╚██████╔╝╚██████╗   ██║   ██║  ██║██║  ██║██║        ██║   ╚██████╔╝██║  ██║",
        "╚═╝  ╚═══╝ ╚═════╝  ╚═════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝        ╚═╝    ╚═════╝ ╚═╝  ╚═╝"
    ]
    print()  # Empty line for spacing
    for line in banner:
        print(f"{PURE_RED}{line}{RESET}")
        time.sleep(0.15)  # Controls the speed of the top-to-bottom animation
    print()  # Empty line for spacing

def create_wav_header(data_size, sample_rate=8000):
    """Generates a standard 44-byte RIFF/WAVE header for 16-bit Mono PCM."""
    channels = 1
    bit_depth = 16
    byte_rate = (sample_rate * channels * bit_depth) // 8
    block_align = (channels * bit_depth) // 8
    
    header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,
        1,          # PCM Format
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bit_depth,
        b'data',
        data_size
    )
    return header

def open_hardware_sco_stream(target_mac, sample_rate=8000):
    print(f"{SKY_BLUE}[*] Targeting Bluetooth Device hardware: {target_mac}{RESET}")
    print(f"{SKY_BLUE}[*] Mode: Flattened Unbreakable Stream Recovery Active.{RESET}")
    print(f"{SKY_BLUE}[*] Press Ctrl+C to stop and save at any time.{RESET}")
    
    captured_bytes = bytearray()
    target_string = str(target_mac).upper()
    silent_padding = b'\x00' * 60
    
    sco_sock = None
    is_connected = False
    last_connection_successful = False
    
    try:
        while True:
            # Step 1: Handle connection if socket is closed or dropped
            if not is_connected:
                try:
                    sco_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, 2)
                    sco_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
                    sco_sock.settimeout(5.0)  # Prevents kernel hanging bugs
                    sco_sock.connect(target_string)
                    sco_sock.setblocking(True)
                    
                    if last_connection_successful:
                        print(f"{SKY_BLUE}[+] Shifting complete! Reconnected to Solid Light phase. Continuing stream...{RESET}")
                    else:
                        print(f"{SKY_BLUE}[+] Connection established. Streaming continuous audio...{RESET}")
                    
                    is_connected = True
                    last_connection_successful = True
                except Exception as conn_err:
                    if sco_sock:
                        sco_sock.close()
                    is_connected = False
                    print(f"{SKY_BLUE}[.] Synchronizing channels. Searching for stable hardware ({conn_err})...{RESET}")
                    time.sleep(0.3)
                    continue

            # Step 2: Read audio bytes if connection is active
            try:
                data = sco_sock.recv(60)
                if not data:
                    print(f"{SKY_BLUE}[!] Remote host closed connection stream descriptor.{RESET}")
                    sco_sock.close()
                    is_connected = False
                    time.sleep(0.3)
                    continue
                    
                captured_bytes.extend(data)
                
                try:
                    sco_sock.send(silent_padding)
                except OSError:
                    pass
                    
            except (OSError, socket.error) as stream_err:
                print(f"{SKY_BLUE}[!] Radio state drop detected: {stream_err}. Re-initializing recovery routine...{RESET}")
                if sco_sock:
                    sco_sock.close()
                is_connected = False
                time.sleep(0.3)
                continue
                
    except KeyboardInterrupt:
        print(f"{SKY_BLUE}\n[*] Monitoring terminated by operator. Compiling file buffers...{RESET}")
        
        if len(captured_bytes) > 0:
            # Clean MAC address for filename usage (remove colons)
            clean_mac_for_file = target_string.replace(":", "-")
            
            # Generates timestamp including milliseconds (%f) to prevent duplicates
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            
            # Dynamic filename including target device MAC and time
            file_name = f"captured_{clean_mac_for_file}_{timestamp}.wav"
            full_path = os.path.abspath(file_name)
            
            print(f"{SKY_BLUE}[*] Committing {len(captured_bytes)} total bytes to audio path...{RESET}")
            header = create_wav_header(len(captured_bytes), sample_rate)
            
            try:
                with open(file_name, "wb") as wav_file:
                    wav_file.write(header)
                    wav_file.write(captured_bytes)
                print(f"{SKY_BLUE}[+] SUCCESS! Drop-free continuous capture compiled perfectly.{RESET}")
                print(f"{SKY_BLUE}[+] Final File Path: {full_path}{RESET}")
            except Exception as write_err:
                print(f"{SKY_BLUE}[-] File write crash: {write_err}{RESET}")
        else:
            print(f"{SKY_BLUE}[-] Error: Execution cut short before any audio data blocks were collected.{RESET}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sudo python3 silent_test.py <TARGET_MAC_ADDRESS>")
        sys.exit(1)
        
    # Trigger the high-density block animated banner
    print_noctraptor_banner()
    
    clean_mac_string = sys.argv[-1]
    open_hardware_sco_stream(clean_mac_string)
