import re

def analyze_llvm_ir(llvm_file):
    with open(llvm_file, 'r') as f:
        ir = f.read()

    # Find all loop comparisons
    loops = re.findall(r'icmp slt i32 (\%\d+), (\%\d+)', ir)
    
    if not loops:
        print("No loop bounds found!")
        return

    print("=== Simplified Loop Analysis ===")
    print(f"Found {len(loops)} loops with bounds:")
    
    # Group identical bounds
    bound_groups = {}
    for var, bound in loops:
        bound_groups.setdefault(bound, []).append(var)

    # Print results
    for bound, vars in bound_groups.items():
        print(f"- Bound {bound} used by {len(vars)} loops (variables: {', '.join(vars)})")

    # Hackathon assumption: Treat the most common bound as N
    main_bound = max(bound_groups.keys(), key=lambda k: len(bound_groups[k]))
    print(f"\nAssuming main bound {main_bound} represents 'N'")

    # Generate PIM ISA template
    print("\n=== PIM Instruction Template ===")
    print("PROG 0x1F  ; Program all cores for 4-bit MAC")
    
    print("\n; Matrix multiplication kernel")
    print(f"; for i in 0..{main_bound}")
    print(f"; for j in 0..{main_bound}")
    print(f"; for k in 0..{main_bound}")
    
    print("""
; Memory access pattern:
; C[i][j] += A[i][k] * B[k][j]
READ [A_addr]  ; Load A[i][k]
READ [B_addr]  ; Load B[k][j]
EXE MAC        ; Multiply-accumulate
WRITE [C_addr] ; Store result""")

    print("\nNote: Replace [A_addr], [B_addr], [C_addr] with actual memory mappings")

if __name__ == "__main__":
    analyze_llvm_ir("matmul.ll")