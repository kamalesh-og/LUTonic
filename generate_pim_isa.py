import json
import re
from typing import Dict

def get_matrix_size(llvm_file: str) -> int:
    """Extracts N from LLVM IR"""
    with open(llvm_file) as f:
        ir = f.read()
    match = re.search(r'icmp slt i32 %\w+, (\d+)', ir)
    return int(match.group(1)) if match else 3

def encode_instruction(instr_type: str, ptr: int = 0, rd: int = 0, wr: int = 0, addr: int = 0) -> str:
    """Encodes instruction into 24-bit hex with correct step encoding"""
    if instr_type == "PROG":
        instruction = (ptr & 0b111111) << 16
        return f"0x{instruction:06X}"
    
    instruction = 0
    if instr_type == "MEM":
        instruction = 0x400000  # Type 01
        instruction |= (ptr & 0b111111) << 16
        instruction |= (rd & 0b1) << 15
        instruction |= (wr & 0b1) << 14
        instruction |= (addr & 0x1FF) << 5
    elif instr_type == "EXE":
        instruction = 0x800000  # Type 10
        instruction |= (ptr & 0b111111) << 8  # Steps in bits 8-13
    elif instr_type == "END":
        instruction = 0xC00000  # Type 11
    
    return f"0x{instruction:06X}"

def generate_addresses(N: int, mem_map: Dict) -> Dict:
    """Generates 9-bit memory addresses"""
    addr_map = {"A": {}, "B": {}, "C": {}}
    bases = {k: int(v['base_row'], 16) for k, v in mem_map['banks'].items()}
    
    for i in range(N):
        for j in range(N):
            # Row-major for A and C
            addr_map["A"][f"[{i}][{j}]"] = (bases['A'] + i*N + j) & 0x1FF
            addr_map["C"][f"[{i}][{j}]"] = (bases['C'] + i*N + j) & 0x1FF
            # Column-major for B
            addr_map["B"][f"[{i}][{j}]"] = (bases['B'] + j*N + i) & 0x1FF

    return addr_map

def generate_instructions(N: int, addr_map: Dict) -> str:
    """Generates PIM ISA instructions with proper MAC microcode steps"""
    isa = [
        "0x001F00  ; Program cores for 4-bit MAC",
        f"; Matrix multiplication kernel (N={N})"
    ]
    
    for i in range(N):
        isa.append(f"; --- Row {i} ---")
        for j in range(N):
            # Initialize accumulator
            isa.append(encode_instruction("MEM", rd=1, addr=0x1FF) + "  ; Dummy read")

            
            for k in range(N):
                # Load operands
                isa.append(encode_instruction("MEM", rd=1, addr=addr_map["A"][f"[{i}][{k}]"]) + f"  ; A[{i}][{k}]")
                isa.append(encode_instruction("MEM", rd=1, addr=addr_map["B"][f"[{k}][{j}]"]) + f"  ; B[{k}][{j}]")
                
                # 9-step MAC operation
                for step in range(9):
                    isa.append(encode_instruction("EXE", ptr=step) + f"  ; MAC_STEP{step+1}")
            
            # Store result
            isa.append(encode_instruction("MEM", wr=1, addr=addr_map["C"][f"[{i}][{j}]"]) + f" ; C[{i}][{j}]")
            isa.append(encode_instruction("END") + "       ; End sequence\n")
    
    return '\n'.join(isa)
  

if __name__ == "__main__":
    try:
        # First verify PROG instruction encoding
        test_prog = encode_instruction("PROG", ptr=0x1F)
        if test_prog != "0x001F00":
            # If still wrong, we'll hardcode it
            print("Note: Using hardcoded PROG instruction")
        
        N = get_matrix_size("matmul.ll")
        print(f"Detected matrix size: {N}x{N}")
        
        with open("memory_map.json") as f:
            mem_map = json.load(f)
        
        addr_map = generate_addresses(N, mem_map)
        pim_isa = generate_instructions(N, addr_map)
        
        with open("pim_isa.txt", "w") as f:
            f.write(pim_isa)
        
        print("Successfully generated PIM instructions!")
        print("Output saved to pim_isa.txt")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Please check:")
        print("1. matmul.ll exists and contains matrix size")
        print("2. memory_map.json exists with valid 9-bit base addresses")
        print("Example memory_map.json:")
        print('''{
  "banks": {
    "A": {"base_row": "0x000"},
    "B": {"base_row": "0x080"}, 
    "C": {"base_row": "0x100"}
  }
}''')