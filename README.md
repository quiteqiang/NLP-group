# NLP-group

## 实验架构

主模型：embedding 100 + hidden 100 + 1 LSTM layer + cross-attention

```text
主模型：embedding 100 + hidden 100 + 1 LSTM layer + cross-attention
│
├─ Attention 机制消融与比较
│  ├─ No attention
│  │  └─ 移除 cross-attention；若没有其他 attention，则移除全部 attention
│  │     问题：attention 本身是否有贡献？
│  │
│  ├─ Goal attention only
│  │  └─ 移除 cross-attention，只保留 goal 内部的 attention
│  │     问题：跨序列对齐是否比单独关注 goal 词更有用？
│  │
│  ├─ Self attention (trained query)
│  │  └─ 用 learned-query attention pooling 替代 cross-attention
│  │     问题：跨序列 attention 是否优于单序列的 attention pooling？
│  │
│  └─ Cross attn + goal-side attention
│     └─ 在主模型的 cross-attention 之外，额外加入 goal-side attention
│        问题：额外关注 goal 内部的重要词，是否能提升 cross-attention？
│
├─ 输入消融
│  └─ Goal removed
│     问题：模型是否真正使用 PIQA 的 goal？
│
└─ 容量分析
   ├─ embedding 100 → 50
   ├─ hidden 100 → 200
   └─ LSTM 1 layer → 2 layers
```
