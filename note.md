
## Goal Attention: 每个词经过 BiLSTM 后会变成一个向量。模型把这个向量和可训练的 goal_query 做匹配，匹配分数越高，分给这个词的权重通常越大。这些权重是在训练中根据答题结果逐步学出来的：模型会调整参数，让预测更准确。它没有人工设定“哪些词重要”的规则。
```python
CONFIG:
attention_type = "none"
goal_attention = True
use_cross_attention = False

GOAL:
goal → embedding → shared BiLSTM
     → goal_attention=True
     → learned goal_query attention
     → goal_vector

SOLUTIONS:
solution 1 ─┐
            ├→ embedding → shared BiLSTM → word vectors
solution 2 ─┘

每个 solution 的 word vectors
    → masked mean pool → context

solution 1 ↔ solution 2
    → cross-attention=False

[goal_vector ; context ; goal_vector*context ;
 |goal_vector-context|] (800)
                 ↓
             MLP → score

shared MLP 给 solution 1、2 分别打分 → softmax
```

## Self Attention: 会给每个 solution 里的词分配不同权重，再用加权结果概括这个 solution。这样重要词对最终评分影响更大。
```python
CONFIG:
attention_type = "self"       → SELF ATTENTION enabled
goal_attention = False
use_cross_attention = False

GOAL:
goal → embedding → shared BiLSTM → masked mean pool → goal_vector

SOLUTIONS:
solution 1 ─┐
            ├→ embedding → shared BiLSTM → word vectors
solution 2 ─┘
                              │
                              ▼
                    SELF ATTENTION
                 learned pool_query scores
                    each solution's words
                              │
                   weighted pooling → context

solution 1 ↔ solution 2
    cross-attention is disabled

[goal_vector ; context ; goal_vector*context ;
 |goal_vector-context|] (800)
                 ↓
             MLP → score

shared MLP scores solution 1 and solution 2 → softmax
```


## Cross-attention 用来比较两个 solution 的词语差异。它先把一个 solution 的词与另一个 solution 中最匹配的词对齐，再提取并汇总两者的差异，交给 MLP 评分。
```python
GOAL:
goal → embedding → shared BiLSTM → masked mean pool → goal_vector

SOLUTIONS:
solution 1 ─┐
            ├→ embedding → shared BiLSTM → word vectors
solution 2 ─┘

每个 solution 的 word vectors → masked mean pool → context

当前 solution ↔ 另一个 solution
    → cross-attention 对齐 → current - aligned_other
    → masked mean pool → difference

[goal_vector ; context ; goal_vector*context ; |goal_vector-context| ;
 difference] (1000)
    ↓
MLP → score

shared MLP 分别给 solution 1、2 打分 → softmax
```

## Cross_attention_plus_goal_attention：
```python
GOAL:
goal → embedding → shared BiLSTM → goal_query attention → goal_vector

SOLUTIONS:
solution 1 ─┐
            ├→ embedding → shared BiLSTM → word vectors
solution 2 ─┘

每个 solution 的 word vectors → masked mean pool → context

当前 solution ↔ 另一个 solution
    → cross-attention 对齐 → current - aligned_other
    → masked mean pool → difference

[goal_vector ; context ; goal_vector*context ; |goal_vector-context| ;
 difference] (1000)
    ↓
MLP → score

shared MLP 分别给 solution 1、2 打分 → softmax
```