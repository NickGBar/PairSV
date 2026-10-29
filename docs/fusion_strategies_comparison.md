# Six ways to fuse a frozen genome model into a CNN

The pileup image and the sequence embedding describe the same genomic window through two different signals. Where you let them meet — input, mid-network, bottleneck, or output — decides how many parameters you add, whether training starts from your image baseline undisturbed, and how much the sequence branch can actually correct the image branch's mistakes.

Legend used throughout: **image / CNN branch**, **frozen sequence embedding**, **fusion point** (where the two meet).

---

## Which one should I pick?

**Short answer:** if you're unsure, start with **mid-level FiLM** or **late context calibration** — both already run in this codebase, and both are built so the model behaves exactly like your existing image-only model on day one, only improving from there as it learns to use the sequence data. FiLM has more room to help; context calibration is simpler and easier to explain. The other four are worth reaching for only once you know that much.

### Plain-language guide (no ML background needed)

| Method | Pros | Cons | Choose this if |
|---|---|---|---|
| **Early fusion** — *bake the sequence info into the picture itself, as if it were extra colors* | • Lets the network blend picture and sequence signals from the very first layer, so it can learn combinations neither would suggest alone.<br>• Simple to describe: "add more channels to the image." | • You can't reuse a model you already trained — the network's first layer has to change shape, so training starts over from zero.<br>• A problem in the sequence data can throw off everything downstream, since it changes what the model sees from the start. | You're training from scratch anyway and don't need to protect or reuse an existing model. |
| **Mid-level FiLM** — *let the sequence data act like a dial that retunes the CNN's filters partway through* | • You can start from a CNN you've already trained and add this on top without breaking what already works.<br>• At the first step of training it behaves exactly like your original model — nothing changes until this part proves useful. | • A bit more setup than the simpler options — it has to be wired into two specific points inside the CNN.<br>• Harder to point to one number and say exactly why the sequence data changed a given prediction. | You already have a working image-only model and want the safest way to add sequence context on top of it. *(What this repo uses today.)* |
| **Bottleneck concat** — *take the two summaries — one from the image, one from the sequence — and glue them together right before the final decision* | • By far the fastest and cheapest to build — a good first experiment.<br>• Easy to explain: two numbers get stapled together and fed into one small decision-maker. | • The sequence data can only nudge the final answer, not change how the image itself gets analyzed — the weakest at actually using context.<br>• Usually delivers the smallest improvement of the options here. | You want a quick, low-effort test of "does sequence data help at all" before investing more engineering time. |
| **Cross-attention** — *let each part of the image individually "ask" the sequence data which parts of it are relevant to it* | • The most powerful option on paper — can pick out exactly the right piece of context for each part of the image, instead of one blended summary for the whole window.<br>• Best suited to long or complicated regions where different parts of the image need different context. | • By far the most complex to build correctly, and the slowest to train and run.<br>• Nobody has tried this on this project yet, so there's more risk of hitting unexpected problems. | The simpler options plateau and you have the engineering time to invest in something more advanced. |
| **Late context calibration** — *let the sequence data cast a vote that can nudge the final decision up or down, without touching anything else* | • Extremely safe: the model behaves exactly like the plain image-only version until this extra vote proves it's useful.<br>• Easy to reason about — "does the surrounding sequence look risky enough to override what the image alone suggests?" | • Limited reach — it can only adjust the final answer, it can't fix a mistake the image model made in reading the picture itself. | You mainly want to catch specific false alarms or missed calls without touching how the image model works. *(Also live in this repo today.)* |
| **Late decision fusion** — *train two separate experts — one on images, one on sequence — and blend their opinions afterward* | • No need to retrain the image model at all — just combine two models you may already have.<br>• The simplest and easiest-to-undo option — swap out either expert without touching the other. | • The two experts never learn from each other during training, so they can miss patterns only visible when both signals are considered together.<br>• Usually the smallest improvement of the six, since it's the least integrated. | You already have both models built separately, or want a low-risk way to blend in an outside prior (e.g. population data) without retraining anything. *(Also live in this repo today.)* |

---

## Quick compare (technical)

| Method | Merge point | Mechanism | New params | Identity at init | In this repo |
|---|---|---|---|---|---|
| Early fusion | Input | embedding → linear/PCA proj → broadcast as extra image channels, concatenated before conv 1 | proj. layer only | no | — |
| Mid-level FiLM | Mid-network | γ,β predicted from embedding modulate CNN feature maps: `F·(1+γ)+β` at two hook depths | 2× tiny MLP (D→128→2C) | **yes** | ✓ `film.py` / `fused_cnn.py` |
| Bottleneck concat | Bottleneck | flattened CNN feature vector concatenated with projected embedding, fed through a joint MLP classifier | 1 MLP head | no | — |
| Cross-attention | Mid-network | CNN spatial map as query attends over embedding tokens (K,V) — per-location relevance, not one pooled vector | Q/K/V + out proj | no | — |
| Late context calibration | Output | a small zero-init MLP predicts a delta added directly to the deletion logit, trained jointly end-to-end | 2× tiny zero-init MLP | **yes** | ✓ `fused_cnn.py` context path |
| Late decision fusion | Output | a separately-trained sequence-prior model's logit is added to the CNN's logit at inference, weighted | separate model + scalar weight | yes | ✓ `train_sequence_prior.py` |

---

## Qualitative scorecard

Architectural judgment, scored 1 (low) → 5 (high) — **not a benchmark result**, read as a prioritization heuristic. Rows marked ● are live in this repo today.

| Method | Integration complexity | Compute overhead added | Representational capacity | Stability at init |
|---|:---:|:---:|:---:|:---:|
| Early fusion | 2 | 1 | 2 | 1 |
| ● Mid-level FiLM | 3 | 2 | 4 | 5 |
| Bottleneck concat | 1 | 1 | 3 | 2 |
| Cross-attention | 5 | 4 | 5 | 2 |
| ● Late context calibration | 2 | 1 | 3 | 5 |
| ● Late decision fusion | 1 | 1 | 2 | 5 |

---

## Six fusion patterns in detail

### 1. Early fusion — input-level channel concat
**Merge point:** Input

```
RGB pileup ──┐
             ├─▶ concat ─▶ CNN conv stack ─▶ P(deletion)
embedding→ch.┘
```
*Changes the input distribution — no identity at init.*

```python
# image: (B,3,H,W)  emb: (B,D) -> projected to (B,K,H,W)
ctx = self.proj(emb).view(B, K, 1, 1).expand(-1, -1, H, W)
x = torch.cat([image, ctx], dim=1)   # (B, 3+K, H, W)
logits = self.cnn(x)                 # CNN's first conv widened to 3+K in
```

**Best when:** You want the CNN to learn joint low-level filters over pixels and sequence together, and can afford a full retrain — no warm start from an image-only checkpoint is possible once the input shape changes.

### 2. Mid-level FiLM — feature-wise linear modulation
**Merge point:** Mid-network *(live in this repo — `film.py` / `fused_cnn.py`)*

```
conv block 1
   │
conv block 2
   │
conv block 3 ◀╌╌╌╌╌╮  γ,β (zero-init)
   │               │
conv block 4 ◀╌╌╌╌╌┴── frozen embedding
   │
P(deletion)
```

```python
gamma, beta = self.film(embedding)          # each (B,C), zero-init
def hook(feat):                              # feat: (B,C,H,W)
    return feat * (1 + gamma.view(B,C,1,1)) + beta.view(B,C,1,1)
logits = self.cnn.forward_with_hook(image, hook3=hook)
```

**Best when:** You want to warm-start from a trained image-only CNN and let sequence context sharpen mid-level features without disturbing behavior at step 0 — the zero-init last layer makes `F_out = F` exactly, until FiLM learns otherwise.

### 3. Bottleneck concatenation — feature vector + MLP head
**Merge point:** Bottleneck

```
CNN conv stack ─▶ flatten (256-d) ─┐
                                    ├─▶ concat ─▶ MLP ─▶ P(deletion)
frozen embedding ─▶ proj (128-d) ──┘
```

```python
feat = self.cnn.penultimate(image)          # (B, 256)
ctx  = self.embed_proj(embedding)            # (B, 128)
joint = torch.cat([feat, ctx], dim=-1)       # (B, 384)
logits = self.head(joint)                    # MLP(384 -> 2)
```

**Best when:** A fast baseline to test whether sequence context helps at all before investing in FiLM hooks or attention — cheapest to implement, but the CNN backbone can't be modulated, so its own errors are unreachable by the sequence branch.

### 4. Cross-attention — spatial query × sequence tokens
**Merge point:** Mid-network

```
Q: spatial map (CNN feature map)  ─┐
                                    ├─▶ softmax attention ─▶ + CNN path ─▶ logits
K,V: sequence tokens (embedding)  ─┘
```

```python
Q = self.q_proj(cnn_map.flatten(2).transpose(1,2))  # (B,HW,d)
K = self.k_proj(seq_tokens)                          # (B,T,d)
V = self.v_proj(seq_tokens)
attn = (Q @ K.transpose(-1,-2) / d**0.5).softmax(-1)
ctx  = (attn @ V).transpose(1,2).view_as(cnn_map)
fused = cnn_map + self.out_proj(ctx)                 # residual merge
```

**Best when:** Sequence context varies meaningfully within the window — e.g. long deletions spanning several repeat elements — and different spatial positions in the pileup need to attend to different parts of the sequence, not a single pooled 256-d summary.

### 5. Late context calibration — zero-init joint logit delta
**Merge point:** Output *(live in this repo — `fused_cnn.py` context path)*

```
CNN conv stack ─▶ z_img ──┐
                           ├─▶ + ─▶ σ(z_img + Δ)
frozen embedding ─▶ Δ≈0 ──┘
```

```python
z_img = self.cnn(image)[:, 1]                 # deletion logit
delta = self.context_delta(embedding)          # zero-init MLP → 0 at step 0
      + self.joint_delta(cat(cnn_feat, ctx_feat))
logits[:, 1] = z_img + delta.squeeze(-1)       # P = softmax(logits)
```

**Best when:** You want a narrow, interpretable "sequence red-flag" correction on top of an otherwise-unmodified CNN decision — good for suppressing false positives in sequence-context-dangerous regions, trained jointly so it can't drift from the image baseline at step 0.

### 6. Late decision fusion — independent models, post-hoc mix
**Merge point:** Output *(live in this repo — `train_sequence_prior.py`)*

```
CNN (trained) ─▶ logit A ──┐
   ╎ trained independently  ├─▶ w·A + B
sequence prior model ─▶ logit B ──┘
```

```python
z_cnn   = cnn_model(image)[:, 1]
z_prior = sequence_prior_model(embedding)[:, 1]  # trained separately
logit   = z_cnn + weight * z_prior + bias        # --sequence-prior-weight
p = torch.sigmoid(logit)
```

**Best when:** You want to reuse an existing prior — e.g. a population-level sequence-context model — without retraining the CNN at all, or need to swap/reweight the prior per-run without touching the image model's weights.

---

## Live in this repo today

Mid-level FiLM (`deepsv/models/film.py`) and late context calibration (`fused_cnn.py`'s `context` path) are combined by default as `film_context` — both are zero-init at step 0, so training starts as an exact identity wrapper around the image-only CNN. Late decision fusion is also live as a separate, optional path (`train_sequence_prior.py` + `--sequence-prior-weight`) for mixing in a population-level prior without retraining the CNN at all.

See [`docs/backbone_comparison_design.md`](backbone_comparison_design.md) for how this maps onto the HyenaDNA / Caduceus / NT-v2 / DNABERT-2 backbone comparison.
