#include <iostream>
#include <fstream>
#include <sstream>
#include <regex>
#include <unordered_map>
#include "json.hpp"
using json = nlohmann::json;

using namespace std;

int getMatrixSize(const string& llvmFile) {
    ifstream file(llvmFile);
    if (!file) {
        cerr << "Error: Unable to open " << llvmFile << endl;
        return 2; // Default N = 3 if file not found
    }

    stringstream buffer;
    buffer << file.rdbuf();
    string ir = buffer.str();
    file.close();

    regex pattern(R"(icmp slt i32 %\w+, (\d+))");
    smatch match;
    if (regex_search(ir, match, pattern)) {
        return stoi(match[1].str());
    }
    return 2; // Default N = 3 if no match found
}

string encodeInstruction(const string& instrType, int ptr = 0, int rd = 0, int wr = 0, int addr = 0) {
    int instruction = 0;

    if (instrType == "PROG") {
        instruction = (ptr & 0b111111) << 16;
    } else if (instrType == "MEM") {
        instruction = 0x400000; // Type 01
        instruction |= (ptr & 0b111111) << 16;
        instruction |= (rd & 0b1) << 15;
        instruction |= (wr & 0b1) << 14;
        instruction |= (addr & 0x1FF) << 5;
    } else if (instrType == "EXE") {
        instruction = 0x800000; // Type 10
        instruction |= (ptr & 0b111111) << 8;
    } else if (instrType == "END") {
        instruction = 0xC00000; // Type 11
    }

    stringstream ss;
    ss << "0x" << hex << uppercase << instruction;
    return ss.str();
}

unordered_map<string, unordered_map<string, int>> generateAddresses(int N, const json& memMap) {
    unordered_map<string, unordered_map<string, int>> addrMap = {{"A", {}}, {"B", {}}, {"C", {}}};
    unordered_map<string, int> bases;

    for (auto& item : memMap["banks"].items()) {
        std::string bank = item.key();
        auto value = item.value();
        bases[bank] = std::stoi(value["base_row"].get<std::string>(), nullptr, 16);
    }
    

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            addrMap["A"]["[" + to_string(i) + "][" + to_string(j) + "]"] = (bases["A"] + i * N + j) & 0x1FF;
            addrMap["C"]["[" + to_string(i) + "][" + to_string(j) + "]"] = (bases["C"] + i * N + j) & 0x1FF;
            addrMap["B"]["[" + to_string(i) + "][" + to_string(j) + "]"] = (bases["B"] + j * N + i) & 0x1FF;
        }
    }

    return addrMap;
}

string generateInstructions(int N, unordered_map<string, unordered_map<string, int>>& addrMap) {
    stringstream isa;
    isa << "0x001F00  ; Program cores for 4-bit MAC\n";
    isa << "; Matrix multiplication kernel (N=" << N << ")\n";

    for (int i = 0; i < N; ++i) {
        isa << "; --- Row " << i << " ---\n";
        for (int j = 0; j < N; ++j) {
            isa << encodeInstruction("MEM", 0, 1, 0, 0x1FF) << "  ; Dummy read\n";

            for (int k = 0; k < N; ++k) {
                isa << encodeInstruction("MEM", 0, 1, 0, addrMap["A"]["[" + to_string(i) + "][" + to_string(k) + "]"])
                    << "  ; A[" << i << "][" << k << "]\n";
                isa << encodeInstruction("MEM", 0, 1, 0, addrMap["B"]["[" + to_string(k) + "][" + to_string(j) + "]"])
                    << "  ; B[" << k << "][" << j << "]\n";

                for (int step = 0; step < 9; ++step) {
                    isa << encodeInstruction("EXE", step) << "  ; MAC_STEP" << step + 1 << "\n";
                }
            }

            isa << encodeInstruction("MEM", 0, 0, 1, addrMap["C"]["[" + to_string(i) + "][" + to_string(j) + "]"])
                << " ; C[" << i << "][" << j << "]\n";
            isa << encodeInstruction("END") << "       ; End sequence\n\n";
        }
    }

    return isa.str();
}

int main() {
    try {
        string test_prog = encodeInstruction("PROG", 0x1F);
        if (test_prog != "0x001F00") {
            cout << "Note: Using hardcoded PROG instruction\n";
        }

        int N = getMatrixSize("matmul.ll");
        cout << "Detected matrix size: " << N << "x" << N << endl;

        ifstream file("memory_map.json");
        if (!file) {
            cerr << "Error: Could not open memory_map.json\n";
            return 1;
        }

        json memMap;
        file >> memMap;
        file.close();

        auto addrMap = generateAddresses(N, memMap);
        string pim_isa = generateInstructions(N, addrMap);

        ofstream outFile("pim_isa.txt");
        if (!outFile) {
            cerr << "Error: Unable to write to pim_isa.txt\n";
            return 1;
        }

        outFile << pim_isa;
        outFile.close();

        cout << "Successfully generated PIM instructions!\n";
        cout << "Output saved to pim_isa.txt\n";

    } catch (const exception& e) {
        cerr << "Error: " << e.what() << endl;
        cerr << "Please check:\n";
        cerr << "1. matmul.ll exists and contains matrix size\n";
        cerr << "2. memory_map.json exists with valid 9-bit base addresses\n";
        cerr << "Example memory_map.json:\n";
        cerr << R"({
  "banks": {
    "A": {"base_row": "0x000"},
    "B": {"base_row": "0x080"},
    "C": {"base_row": "0x100"}
  }
})" << endl;
    }

    return 0;
}
