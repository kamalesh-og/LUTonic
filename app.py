from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import traceback

app = Flask(__name__)
CORS(app)

MEMORY_MAP = {
    "banks": {
        "A": {"bank_id": 0, "base_row": "0x000"},
        "B": {"bank_id": 1, "base_row": "0x080"},
        "C": {"bank_id": 2, "base_row": "0x100"}
    }
}

def analyze_code(cpp_code):
    """Enhanced code analysis with support for all test cases"""
    analysis = {
        'matrix_size': None,
        'is_dynamic': False,
        'has_matrix_operation': False,
        'is_square': True,
        'dimensions': None,  # Will store (rows1, cols1, rows2, cols2)
        'errors': []
    }

    # Pattern to match matrix operations
    matrix_ops = [
        r'\w+\s*\[[^]]+\]\s*\[[^]]+\]',  # Matrix accesses
        r'for\s*\([^;]*;[^;]*;[^)]*\)\s*{.*\w+\s*=\s*\w+\s*\*\s*\w+',  # Multiplication pattern
        r'\w+\s*=\s*\w+\s*\*\s*\w+'  # Simple multiplication
    ]

    # Check if code contains matrix operations
    analysis['has_matrix_operation'] = any(re.search(pattern, cpp_code) for pattern in matrix_ops)

    # Extract all matrix declarations
    matrix_decls = re.finditer(
        r'(?:int|float|double)\s+(\w+)\s*((?:\[[^]]+\]){2})', 
        cpp_code
    )

    matrices = {}
    for decl in matrix_decls:
        name = decl.group(1)
        dims = [d.strip('[]') for d in re.findall(r'\[([^]]+)\]', decl.group(2))]
        matrices[name] = dims

    # Check function parameters for dynamic matrices
    params = re.finditer(
        r'(?:int|float|double)\s+(\w+)((?:\[[^]]*\]){1,2})', 
        re.search(r'\(([^)]*)\)', cpp_code).group(1)
    )

    for param in params:
        name = param.group(1)
        dims = [d.strip('[]') for d in re.findall(r'\[([^]]*)\]', param.group(2))]
        if name in matrices:
            matrices[name] = dims

    # Determine matrix dimensions and check validity
    if len(matrices) >= 2:
        # Get first two matrices (assuming A and B)
        matrix_names = list(matrices.keys())
        a_dims = matrices[matrix_names[0]]
        b_dims = matrices[matrix_names[1]]
        
        # Check if dimensions are compatible
        if len(a_dims) == 2 and len(b_dims) == 2:
            # Check if inner dimensions match (a_cols == b_rows)
            if a_dims[1] != b_dims[0] and a_dims[1] != '' and b_dims[0] != '':
                analysis['errors'].append(f"Incompatible matrix dimensions: {a_dims[1]} != {b_dims[0]}")
                analysis['is_square'] = False
            
            analysis['dimensions'] = (a_dims[0], a_dims[1], b_dims[0], b_dims[1])
            
            # Check if square matrix
            if a_dims[0] == a_dims[1] == b_dims[0] == b_dims[1]:
                if a_dims[0].isdigit():
                    analysis['matrix_size'] = int(a_dims[0])
                else:
                    analysis['is_dynamic'] = True
                    analysis['matrix_size'] = a_dims[0]  # Store the variable name
            else:
                analysis['is_square'] = False

    return analysis

def encode_instruction(instr_type, ptr=0, rd=0, wr=0, addr=0):
    """Instruction encoding remains the same"""
    instruction = 0
    if instr_type == "PROG":
        instruction = (ptr & 0b111111) << 16
    elif instr_type == "MEM":
        instruction = 0x400000
        instruction |= (ptr & 0b111111) << 16
        instruction |= (rd & 0b1) << 15
        instruction |= (wr & 0b1) << 14
        instruction |= (addr & 0x1FF) << 5
    elif instr_type == "EXE":
        instruction = 0x800000
        instruction |= (ptr & 0b111111) << 8
    elif instr_type == "END":
        instruction = 0xC00000
    return f"0x{instruction:06X}"

def generate_addresses(N, mem_map, is_square=True):
    """Generate addresses with support for rectangular matrices"""
    addr_map = {"A": {}, "B": {}, "C": {}}
    bases = {
        "A": int(mem_map["banks"]["A"]["base_row"], 16),
        "B": int(mem_map["banks"]["B"]["base_row"], 16),
        "C": int(mem_map["banks"]["C"]["base_row"], 16)
    }

    if isinstance(N, tuple):  # Rectangular case (M, N, P)
        M, N, P = N
        for i in range(M):
            for j in range(N):
                addr_map["A"][f"[{i}][{j}]"] = (bases["A"] + i * N + j) & 0x1FF
        for i in range(N):
            for j in range(P):
                addr_map["B"][f"[{i}][{j}]"] = (bases["B"] + i * P + j) & 0x1FF
        for i in range(M):
            for j in range(P):
                addr_map["C"][f"[{i}][{j}]"] = (bases["C"] + i * P + j) & 0x1FF
    else:  # Square case
        for i in range(N):
            for j in range(N):
                addr_map["A"][f"[{i}][{j}]"] = (bases["A"] + i * N + j) & 0x1FF
                addr_map["C"][f"[{i}][{j}]"] = (bases["C"] + i * N + j) & 0x1FF
                addr_map["B"][f"[{i}][{j}]"] = (bases["B"] + j * N + i) & 0x1FF  # Transposed for B
    return addr_map

def generate_isa_instructions(N, addr_map, is_square=True):
    """Generate ISA instructions for both square and rectangular matrices"""
    isa = []
    isa.append(f"{encode_instruction('PROG', 0x1F)}  ; Program cores for 4-bit MAC")
    
    if isinstance(N, tuple):  # Rectangular case (M, N, P)
        M, N, P = N
        isa.append(f"; Rectangular matrix multiplication kernel ({M}x{N} * {N}x{P})")
        for i in range(M):
            isa.append(f"; --- Row {i} ---")
            for j in range(P):
                isa.append(f"{encode_instruction('MEM', 0, 1, 0, 0x1FF)}  ; Dummy read")
                for k in range(N):
                    isa.append(f"{encode_instruction('MEM', 0, 1, 0, addr_map['A'][f'[{i}][{k}]'])}  ; A[{i}][{k}]")
                    isa.append(f"{encode_instruction('MEM', 0, 1, 0, addr_map['B'][f'[{k}][{j}]'])}  ; B[{k}][{j}]")
                    for step in range(9):
                        isa.append(f"{encode_instruction('EXE', step)}  ; MAC_STEP{step + 1}")
                isa.append(f"{encode_instruction('MEM', 0, 0, 1, addr_map['C'][f'[{i}][{j}]'])}  ; C[{i}][{j}]")
                isa.append(f"{encode_instruction('END')}       ; End sequence")
                isa.append("")
    else:  # Square case
        isa.append(f"; Square matrix multiplication kernel ({N}x{N})")
        for i in range(N):
            isa.append(f"; --- Row {i} ---")
            for j in range(N):
                isa.append(f"{encode_instruction('MEM', 0, 1, 0, 0x1FF)}  ; Dummy read")
                for k in range(N):
                    isa.append(f"{encode_instruction('MEM', 0, 1, 0, addr_map['A'][f'[{i}][{k}]'])}  ; A[{i}][{k}]")
                    isa.append(f"{encode_instruction('MEM', 0, 1, 0, addr_map['B'][f'[{k}][{j}]'])}  ; B[{k}][{j}]")
                    for step in range(9):
                        isa.append(f"{encode_instruction('EXE', step)}  ; MAC_STEP{step + 1}")
                isa.append(f"{encode_instruction('MEM', 0, 0, 1, addr_map['C'][f'[{i}][{j}]'])}  ; C[{i}][{j}]")
                isa.append(f"{encode_instruction('END')}       ; End sequence")
                isa.append("")
    
    return "\n".join(isa)

@app.route('/compile', methods=['POST'])
def compile_code():
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'cpp')
        user_size = data.get('size', None)
        user_sizes = data.get('sizes', None)  # For rectangular matrices [M, N, P]

        if not code.strip():
            return jsonify({'success': False, 'error': 'Empty code submitted'})

        analysis = analyze_code(code)
        
        if not analysis['has_matrix_operation']:
            return jsonify({
                'success': True,
                'isa_instructions': "// No matrix operations detected in the code",
                'memory_info': {
                    'matrix_size': None,
                    'memory_map': {},
                    'requires_size_input': False,
                    'is_square': True
                }
            })

        if analysis['errors']:
            return jsonify({
                'success': False,
                'error': analysis['errors'][0],
                'requires_size_input': False
            })

        # Handle dynamic sizes
        requires_size_input = analysis['is_dynamic']
        matrix_size = None
        is_square = analysis['is_square']

        if not is_square:
            if not user_sizes or len(user_sizes) != 3:
                return jsonify({
                    'success': False,
                    'error': 'For rectangular matrices, please provide all three dimensions [M, N, P]',
                    'requires_dimensions_input': True
                })
            try:
                M, N, P = map(int, user_sizes)
                if any(d <= 0 or d > 256 for d in [M, N, P]):
                    raise ValueError("Dimensions must be between 1 and 256")
                if N != user_sizes[1]:
                    raise ValueError("Inner dimensions must match (A cols == B rows)")
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f"Invalid dimensions: {str(e)}",
                    'requires_dimensions_input': True
                })
            dimensions = (M, N, P)
        elif requires_size_input:
            if not user_size:
                return jsonify({
                    'success': False,
                    'error': 'Matrix size (N) is required for dynamic matrices',
                    'requires_size_input': True
                })
            try:
                matrix_size = int(user_size)
                if matrix_size <= 0 or matrix_size > 256:
                    raise ValueError("Size must be between 1 and 256")
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': f"Invalid size: {str(e)}",
                    'requires_size_input': True
                })
        else:
            matrix_size = analysis['matrix_size']

        # Generate memory addresses and ISA
        addr_map = generate_addresses(dimensions if not is_square else matrix_size, MEMORY_MAP, is_square)
        isa_instructions = generate_isa_instructions(dimensions if not is_square else matrix_size, addr_map, is_square)

        return jsonify({
            'success': True,
            'isa_instructions': isa_instructions,
            'memory_info': {
                'matrix_size': matrix_size if is_square else f"{dimensions[0]}x{dimensions[1]} * {dimensions[1]}x{dimensions[2]}",
                'memory_map': MEMORY_MAP,
                'requires_size_input': requires_size_input,
                'is_square': is_square,
                'dimensions': dimensions if not is_square else None
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

if __name__ == '__main__':
    app.run(port=5000, debug=True)