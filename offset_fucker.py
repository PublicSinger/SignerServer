#!/usr/bin/env python3

import r2pipe
import sys
import os
import json

magic_code = "488b338b530829f24c8d44"

def analyze_node_file_optimized(file_path):
    if not os.path.exists(file_path):
        print(f"err: file {file_path} not exist")
        return None
    
    try:
        r2 = r2pipe.open(file_path)
        magic_addr = r2.cmd(f"/x {magic_code}").split(" ")[0]
        pds = json.loads(r2.cmd(f"pdj @ {magic_addr}"))
        for pd in pds:
            if "call " in pd["opcode"]:
                return pd["opcode"].split(" ")[-1]
    except Exception as e:
        print(f"failed to analyze: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        try:
            r2.quit()
        except:
            pass

def main():
    if len(sys.argv) != 2:
        print("usage: python3 analyze_node.py <file.node>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    result = analyze_node_file_optimized(file_path)
    
    if result:
        offset = result
        print(f"offset: {offset}")
    else:
        print("failed")

if __name__ == "__main__":
    main()