# LUTonic - The LLVM-to-pPIM Compiler for Energy-Efficient Matrix Acceleration

<table>
  <tr>
    <td>
      <p><strong>📄 Reference Paper</strong></p>
      <a href="https://ieeexplore.ieee.org/document/9643747">
        <img src="https://img.shields.io/badge/Paper-Flexible%20ISA%20for%20pPIM-blue" alt="Paper" />
      </a>
    </td>
    <td style="padding-left: 30px;">
      <p><strong>📘 Project Documentation</strong></p>
      <a href="https://drive.google.com/drive/u/0/folders/1mj00cEZ2JJLR6351LXnHfuNqv-8rOHub">
        <img src="https://img.shields.io/badge/Docs-Project%20Documentation-green" alt="Docs" />
      </a>
    </td>
  </tr>
</table>

This repository implements a compiler that transforms C++ matrix operations into custom ISA instructions for **LUT-based Processing-in-Memory (pPIM)** architectures, as described in *Ganguly et al. (2023)*. The toolchain enables energy-efficient execution of AI/ML workloads directly in DRAM.

## Architecture Overview  
The compiler workflow bridges conventional programming models with pPIM's non-von Neumann architecture:  
![image](https://github.com/user-attachments/assets/af03f1ce-f6dd-432e-833d-87f9dd2e5af2)
*Fig. 1: From C++ to pPIM ISA via LLVM IR*

## Key Features  
- **24-bit ISA Compliance**: Exact encoding matching pPIM paper (Section IV-D)  
- **Automated Microcode Generation**: 9-step MAC operations (Table II)  
- **Memory Optimization**:  
  - Row-major (A/C) and column-major (B) mapping  
  - 9-bit DRAM row addressing (0x000-0x1FF)  
- **Dual Implementation**:  
  - Python (for rapid prototyping)  
  - C++ (for production-grade codegen)  

## Why LUTonic?  
Modern AI faces the **"memory wall"** bottleneck. Our solution:  
1. **Eliminates Data Movement** by computing in DRAM (Section I of paper)  
2. **Precision-Scalable** via programmable LUTs (4-bit/8-bit modes)  
3. **Hardware-Accurate** ISA generation for pPIM clusters (Fig. 1b)  

### Our Website 
![image](https://github.com/user-attachments/assets/0c777637-0b27-418c-a906-0f7bf61593c4)
##### (*Not yet deployed*)

## Key Features of our PIM Compiler Website

- 🧠 **PIM-Based Compiler** for converting C/C++ matrix operations into custom PIM ISA instructions  
- 📐 **Dynamic & Static Matrix Size Support** via `N` input field  
- ⚡ **Optimized for AI/ML Workloads**, especially matrix-heavy operations  
- 🧩 **Tiled Execution Logic** for better parallel processing  
- 🧾 **Physical Memory Mapping Generator** for input/output matrices  
- 🖊️ **Built-in Code Editor** with syntax highlighting and templates  
- 🛠️ **Real-Time ISA Instruction Output** on clicking "Compile & Translate"  
- 🎯 **Responsive & Clean UI** using JetBrains Mono & Inter fonts  
- 🧹 **One-Click Reset** to clear input and output areas  
- ℹ️ **About Modal & Documentation Link** for team info and project goals  
- 🚀 **Fast & Lightweight Web App**—no installation needed  

## Getting Started
### Prerequisites
- **LLVM 14+** (for IR generation)
- **Python 3.8+** or **C++17 compiler**
- `memory_map.json` (configuration file)

## How It Works  
### 1. Input Specification  
```cpp 
// matmul.cpp  
void matmul(int N, int A[N][N], int B[N][N], int C[N][N]) {
  for(int i=0; i<N; i++)
    for(int j=0; j<N; j++)
      for(int k=0; k<N; k++) 
        C[i][j] += A[i][k] * B[k][j];
}
```

### 2.Output ISA Example
```asm
0x001F00  ; PROG cores for 4-bit MAC
0x408000  ; A[0][0]
0x409000  ; B[0][0] 
0x800000  ; MAC_STEP1
...
0xC00000  ; END
```

### Usage

#### Python Version
```bash
python generate_pim_isa.py matmul.ll
```

#### C++ Version
```bash
g++ -std=c++17 generate_PIM_isa.cpp -o lutonic
./lutonic matmul.ll
```

## Benchmark Results
| Operation   | Throughput | Energy Efficiency |
|-------------|------------|-------------------|
| 8-bit MAC   | 1,420 GOPS | 3.18 pJ/OP        |
| 4-bit MAC   | 2,880 GOPS | 2.16 pJ/OP        |
*(Matches paper's Section V-B results)*

## Acknowledgments
- Dr. Ganguly et al. for the **pPIM architecture paper**.
- LLVM community for compiler infrastructure.

## Team
- **[Kamalesh (Myself)](https://github.com/kamalesh-og)** - Responsible for LLVM IR analysis & ISA codegen, C++ optimization for production, Python prototype development, Memory mapping logic, Verification against pPIM specs, Performance benchmarking
- **[Mythri Vellanki](https://github.com/mythri1010)** - Worked on the Website and Code Management
