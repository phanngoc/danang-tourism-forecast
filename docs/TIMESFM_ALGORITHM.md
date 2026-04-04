# 🧠 Cách Train TimesFM — Chi tiết thuật toán

---

### TỔNG QUAN: "GPT cho Time Series"

Cách train TimesFM **gần như giống hệt** cách train GPT/LLM, chỉ thay **token text → patch số liệu**:

```
GPT:     "Tôi" → "đi" → "học" → [dự đoán: "bài"]
TimesFM: [32 giá] → [32 giá] → [32 giá] → [dự đoán: 128 giá tiếp]
```

---

### BƯỚC 1: PATCHING — Tokenize chuỗi số

Thay vì tokenize text thành words, TimesFM **chia chuỗi thời gian thành patches**:

```
Input: [y₁, y₂, y₃, ... y₅₁₂]  (512 ngày giá)
                ↓ chia patches
Patch 1: [y₁ ... y₃₂]      ← 32 điểm = 1 "token"
Patch 2: [y₃₃ ... y₆₄]
Patch 3: [y₆₅ ... y₉₆]
...
Patch 16: [y₄₈₁ ... y₅₁₂]
```

**Input patch = 32 điểm, Output patch = 128 điểm** (dự đoán dài hơn input 4x)

Tại sao patching?
- Giảm sequence length 32× → transformer nhanh hơn
- 1 patch chứa đủ thông tin local (trend ngắn hạn, noise level)
- Giống ViT (Vision Transformer) chia ảnh thành patches

---

### BƯỚC 2: INPUT ENCODING

Mỗi patch được encode thành vector 1280 chiều:

```
                    patch [32 giá] + mask [32 bit]
                              ↓ concat
                         [64 chiều]
                              ↓
                    ┌─────────────────────┐
                    │   Residual Block    │
                    │  Linear(64→1280)    │
                    │  SiLU activation    │
                    │  Linear(1280→1280)  │
                    │  + Skip connection  │
                    └─────────────────────┘
                              ↓
                    token vector [1280 chiều]
                              ↓
                    + Rotary Position Embedding (RoPE)
```

**Mask** rất quan trọng: đánh dấu vị trí nào là padding (không có data thật). Được concat trực tiếp vào input để model biết chỗ nào đáng tin.

---

### BƯỚC 3: TRANSFORMER DECODER — Core algorithm

**20 layers Transformer** với causal attention (giống GPT):

```
Token₁ → Token₂ → Token₃ → ... → Token₁₆
  ↓        ↓        ↓              ↓
  ┌────────────────────────────────────┐
  │         Layer 1/20                  │
  │                                    │
  │  ① RMSNorm                        │
  │  ② Multi-Head Causal Attention    │
  │     • 16 heads × 80d = 1280d      │
  │     • Fused QKV (hiệu quả hơn)    │
  │     • RoPE (vị trí tương đối)      │
  │     • Per-dim scaling (thay 1/√d)  │
  │     • CAUSAL mask: token chỉ nhìn  │
  │       được các token TRƯỚC nó      │
  │  ③ Residual connection             │
  │  ④ RMSNorm → FFN (SiLU) → Residual│
  └────────────────────────────────────┘
              × 20 layers
                    ↓
            Output embeddings [1280d mỗi token]
```

**Causal Attention** = điểm mấu chốt:
```
Token₃ chỉ attend tới Token₁, Token₂, Token₃
(KHÔNG thấy Token₄, ₅, ... — tương lai bị che)

→ Giống GPT: dự đoán next token chỉ dựa trên quá khứ
→ Cho phép train song song trên toàn bộ sequence
```

---

### BƯỚC 4: OUTPUT — Dự đoán 128 điểm tiếp theo

Mỗi output token → 2 heads:

```
Output embedding [1280d]
        ↓                          ↓
┌───────────────┐        ┌──────────────────┐
│  Point Head   │        │  Quantile Head   │
│ ResBlock      │        │  ResBlock        │
│ 1280→1280→1280│        │  1280→1280→10240 │
│ → 128 values  │        │  → 1024×10       │
│ (trung bình)  │        │  (10 quantiles)  │
└───────────────┘        └──────────────────┘
        ↓                          ↓
  [ŷ₁...ŷ₁₂₈]            [q10, q20...q90]
  point forecast          confidence intervals
```

**Output patch dài hơn input 4×** (128 vs 32) — trade-off:
- Ít bước autoregressive hơn → ít error accumulation
- Nhưng khó dự đoán xa hơn

---

### BƯỚC 5: LOSS FUNCTION — MSE

```
Loss = (1/N) × Σ MSE(ŷ_predicted, y_actual)

Tính cho MỌI token trong sequence cùng lúc:

Token₁ dự đoán y₃₃..y₁₆₀   → MSE₁
Token₂ dự đoán y₆₅..y₁₉₂   → MSE₂
Token₃ dự đoán y₉₇..y₂₂₄   → MSE₃
...
Loss = mean(MSE₁, MSE₂, MSE₃, ...)
```

Decoder-only → **train song song** tất cả positions trong 1 forward pass (giống GPT).

---

### BƯỚC 6: MASKING TRICK — Học mọi context length

Vấn đề: nếu train patch đều đặn, model chỉ giỏi khi context = bội số của 32.

Giải pháp: **Random front masking**

```
Mỗi sample, random r ∈ [0, 31]:
- Mask r điểm đầu tiên của patch 1

Ví dụ r=4:
Patch 1: [MASK, MASK, MASK, MASK, y₅, y₆, ... y₃₂]
→ Model thấy 28 điểm → dự đoán next 128

Ví dụ r=20:
Patch 1: [MASK×20, y₂₁, ... y₃₂]  
→ Model thấy 12 điểm → dự đoán next 128

Lặp lại qua tất cả r = 0..31
→ Model đã thấy MỌI context length từ 1 đến max
```

---

### BƯỚC 7: REVERSIBLE INSTANCE NORMALIZATION (RevIN)

Thuật toán normalize **on-the-fly per patch** bằng running statistics:

```python
# Forward: normalize trước transformer
For each patch i:
    update running (n, μ, σ) using Welford's algorithm
    normalized_patch = (patch - μ) / σ

# Transformer xử lý normalized data
output = Transformer(normalized_patches)

# Reverse: denormalize sau transformer  
forecast = output × σ + μ
```

Tại sao quan trọng?
- Stock giá 1,684 vs giá 27 → scale khác nhau hoàn toàn
- RevIN giúp model xử lý **mọi scale** mà không cần biết trước
- Đảm bảo: `f(aX + b) = a·f(X) + b`

---

### BƯỚC 8: INFERENCE — Autoregressive Decoding

```
Input: 512 ngày giá
        ↓
[Prefill] Chạy toàn bộ 16 patches qua transformer
        ↓ KV-Cache lưu lại
Output patch cuối → 128 ngày dự đoán (D+1 → D+128)
        ↓
Nếu cần thêm (horizon > 128):
  Lấy 128 giá vừa dự đoán → chia 4 patches mới
        ↓ KV-Cache (chỉ tính 4 patches mới)
  Output → thêm 128 ngày (D+129 → D+256)
        ↓
  Lặp lại...
```

**KV-Cache** giống LLM inference: không tính lại attention cho patches cũ, chỉ append mới → nhanh hơn nhiều.

---

### TỔNG KẾT PIPELINE TRAINING

```
╔══════════════════════════════════════════════════╗
║  Training Data (100B timepoints)                  ║
║  Google Trends + Wikipedia + Synthetic + M4       ║
╚══════════════════════╦═══════════════════════════╝
                       ↓
            Random front masking (r ∈ [0,31])
                       ↓
            Patching (32 điểm/patch)
                       ↓
            RevIN normalize (per-patch running stats)
                       ↓
            ResidualBlock tokenizer (→1280d)
                       ↓
            20× Transformer layers (causal attention)
                       ↓
            Output heads (point + quantile)
                       ↓
            MSE Loss (tất cả positions song song)
                       ↓
            AdamW optimizer, mini-batch SGD
                       ↓
╔══════════════════════════════════════════════════╗
║  Pretrained Model (200M params)                   ║
║  Zero-shot: nhận chuỗi bất kỳ → forecast          ║
╚══════════════════════════════════════════════════╝
```

### So sánh với GPT

| | GPT | TimesFM |
|---|---|---|
| Input | Text tokens | Patches 32 số |
| Output | 1 token | 128 số |
| Attention | Causal | Causal |
| Position | Learned / RoPE | RoPE |
| Normalization | LayerNorm | RMSNorm + RevIN |
| Loss | Cross-entropy | MSE |
| Params | 175B (GPT-3) | 200M |
| Training data | Text internet | Time series 100B points |
| Inference | 1 token/step | 128 values/step |

Điểm khác biệt lớn nhất: **output patch dài hơn input** (128 vs 32) — TimesFM "nhìn ít, đoán nhiều" trong mỗi bước, giảm autoregressive error.

---

### Tham khảo

- **Paper:** [A decoder-only foundation model for time-series forecasting](https://arxiv.org/abs/2310.10688) (ICML 2024)
- **Code:** [github.com/google-research/timesfm](https://github.com/google-research/timesfm)
- **Model:** [Hugging Face: google/timesfm-2.5-200m-pytorch](https://huggingface.co/google/timesfm-2.5-200m-pytorch)
- **Blog:** [Google Research Blog](https://research.google/blog/a-decoder-only-foundation-model-for-time-series-forecasting/)
