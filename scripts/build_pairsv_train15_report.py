"""Generate the controlled Train15 interim tables, figures, bootstrap and report."""
import json
from pathlib import Path
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_fscore_support,roc_auc_score,average_precision_score
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image
from reportlab.lib.styles import getSampleStyleSheet
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'reports'; FIG=OUT/'figures'; SRC=ROOT/'kaggle/deepsv-ms-train15-controlled/output-v1'
pred=pd.read_csv(SRC/'pairsv_train15_controlled_predictions.csv'); metrics=json.loads((SRC/'pairsv_train15_controlled_metrics.json').read_text()); abl=json.loads((SRC/'pairsv_train15_controlled_ablations.json').read_text())
main=[]
for m in ['M0','M2','M4']:
 x=metrics[m]['selected'];main.append({'model':m,**x})
main=pd.DataFrame(main);main.to_csv(OUT/'pairsv_train15_main_metrics.csv',index=False)
def score(d):
 if len(d)==0:return {'n':0,'precision':np.nan,'recall':np.nan,'f1':np.nan,'roc_auc':np.nan,'pr_auc':np.nan,'specificity':np.nan}
 y=d.label.values;p=d.prediction.values;has_pos=bool((y==1).any());has_neg=bool((y==0).any())
 tn=int(((y==0)&(p==0)).sum());fp=int(((y==0)&(p==1)).sum());specificity=tn/(tn+fp) if has_neg and (tn+fp)>0 else np.nan
 if not has_pos:
  # positive-class precision/recall/F1 are undefined with zero actual positives in the slice
  # (e.g. an all-negative same-site subgroup); specificity is the informative metric there.
  return {'n':len(d),'precision':np.nan,'recall':np.nan,'f1':np.nan,'roc_auc':np.nan,'pr_auc':np.nan,'specificity':specificity}
 pr,re,f,_=precision_recall_fscore_support(y,p,average='binary',zero_division=0)
 roc=roc_auc_score(y,d.probability) if has_neg else np.nan;pra=average_precision_score(y,d.probability) if has_neg else np.nan
 return {'n':len(d),'precision':pr,'recall':re,'f1':f,'roc_auc':roc,'pr_auc':pra,'specificity':specificity}
rows=[]
for m,g in pred.groupby('model'):
 for name,q in [('50–200 bp',(g.length>=50)&(g.length<=200)),('200–1,000 bp',(g.length>200)&(g.length<=1000)),('1,000–10,000 bp',(g.length>1000)),('same-site negatives',(g.label==0)&(g.negative_type=='same_site_negative')),('GT 0/1',(g.label==1)&(g.genotype=='0/1')),('GT 1/1',(g.label==1)&(g.genotype=='1/1'))]:rows.append({'model':m,'subgroup':name,**score(g[q])})
 for s,d in g.groupby('sample'):rows.append({'model':m,'subgroup':'sample:'+s,**score(d)})
sub=pd.DataFrame(rows);sub.to_csv(OUT/'pairsv_train15_subgroup_metrics.csv',index=False)
boot=[];rng=np.random.default_rng(20260720)
wide=pred.pivot(index='row_id',columns='model',values=['label','prediction','probability']);y=wide['label']['M0'].astype(int).values
for a,b in [('M0','M2'),('M0','M4'),('M2','M4')]:
 vals=[]
 for i in range(1000):
  ix=rng.integers(0,len(y),len(y));fa=precision_recall_fscore_support(y[ix],wide['prediction'][a].values[ix],average='binary',zero_division=0)[2];fb=precision_recall_fscore_support(y[ix],wide['prediction'][b].values[ix],average='binary',zero_division=0)[2];vals.append((fb-fa,average_precision_score(y[ix],wide['probability'][b].values[ix])-average_precision_score(y[ix],wide['probability'][a].values[ix])))
 v=np.array(vals);boot.append({'comparison':f'{b} − {a}','n_bootstrap':1000,'f1_difference':v[:,0].mean(),'f1_ci_low':np.quantile(v[:,0],.025),'f1_ci_high':np.quantile(v[:,0],.975),'f1_win_proportion':np.mean(v[:,0]>0),'pr_auc_difference':v[:,1].mean()})
pd.DataFrame(boot).to_csv(OUT/'pairsv_train15_bootstrap.csv',index=False)
ar=[]
for k,v in abl.items():ar.append({'intervention':k,**v})
pd.DataFrame(ar).to_csv(OUT/'pairsv_train15_ablations.csv',index=False)
plt.style.use('seaborn-v0_8-whitegrid')
fig,ax=plt.subplots(figsize=(6,3.4));ax.bar(main.model,main.f1,color=['#4C78A8','#F58518','#54A24B']);ax.set_ylim(.75,.83);ax.set_ylabel('Validation F1');ax.set_title('Controlled Train15 comparison');
for i,v in enumerate(main.f1):ax.text(i,v+.001,f'{v:.3f}',ha='center');fig.tight_layout();fig.savefig(FIG/'main_comparison.png',dpi=220);fig.savefig(FIG/'main_comparison.pdf');plt.close(fig)
short=sub[sub.subgroup=='50–200 bp'];fig,ax=plt.subplots(figsize=(6,3.4));ax.bar(short.model,short.recall,color=['#4C78A8','#F58518','#54A24B']);ax.set_ylim(.7,.9);ax.set_ylabel('Positive recall');ax.set_title('Short-deletion recall (50–200 bp)');fig.tight_layout();fig.savefig(FIG/'short_deletion_recall.png',dpi=220);fig.savefig(FIG/'short_deletion_recall.pdf');plt.close(fig)
ab=pd.DataFrame(ar);fig,ax=plt.subplots(figsize=(7,3.4));ax.barh(ab.intervention,ab.f1_change,color='#E45756');ax.axvline(0,color='black');ax.set_xlabel('F1 change from full M4');ax.set_title('M4 branch interventions');fig.tight_layout();fig.savefig(FIG/'branch_ablations.png',dpi=220);fig.savefig(FIG/'branch_ablations.pdf');plt.close(fig)
fig,ax=plt.subplots(figsize=(7,3.4));ax.axis('off');ax.text(.02,.72,'Candidate locus',fontsize=16,weight='bold');ax.text(.42,.72,'Individual A: deletion GT 0/1 or 1/1',fontsize=12,bbox={'facecolor':'#54A24B','alpha':.2});ax.text(.42,.35,'Individual B: same locus, GT 0/0',fontsize=12,bbox={'facecolor':'#E45756','alpha':.2});ax.annotate('',xy=(.4,.62),xytext=(.25,.62),arrowprops={'arrowstyle':'->'});ax.annotate('',xy=(.4,.42),xytext=(.25,.42),arrowprops={'arrowstyle':'->'});ax.set_title('Same-site genotype-level design');fig.tight_layout();fig.savefig(FIG/'dataset_design.png',dpi=220);fig.savefig(FIG/'dataset_design.pdf');plt.close(fig)
fig,ax=plt.subplots(figsize=(7,3.4));ax.axis('off');ax.text(.02,.75,'Left pileup + Right pileup',fontsize=12,bbox={'facecolor':'#4C78A8','alpha':.2});ax.text(.38,.75,'Tied CNN',fontsize=12);ax.text(.63,.75,'Image path',fontsize=12);ax.text(.02,.35,'REF/ALT embedding  •  Read embedding  •  17 scalars',fontsize=12,bbox={'facecolor':'#54A24B','alpha':.2});ax.text(.63,.35,'Residual late fusion → deletion probability',fontsize=12);ax.set_title('PAIR-SV architecture');fig.tight_layout();fig.savefig(FIG/'architecture.png',dpi=220);fig.savefig(FIG/'architecture.pdf');plt.close(fig)
b=pd.DataFrame(boot);mainmd=main.round(4).to_markdown(index=False);bootmd=b.round(4).to_markdown(index=False);abmd=pd.DataFrame(ar).round(4).to_markdown(index=False)
text=f'''# PAIR-SV Train15 interim report

## Abstract

This interim validation experiment evaluates PAIR-SV on a frozen multisample snapshot of 15 training individuals and five validation individuals (29,924 and 9,981 successful sample–candidate examples). It is **not** the final 40/5/5 experiment and no internal-test person was accessed. Controlled fixed-seed M0, M2 and M4 runs use identical examples, five epochs, train-only normalization and validation-only threshold selection. M4 has the highest F1, but its margin over M2 is small; conclusions therefore remain cautious.

## Motivation, data and split

The question is whether paired breakpoint images benefit from sample-specific read support and candidate-aware REF/ALT representation. Positives are PanGenie GT 0/1 or 1/1 high-quality sequence-resolved deletions; negatives are same-site callable 0/0 genotypes. This design holds the candidate locus fixed across people and tests genotype-specific evidence. The person split is frozen: 15 train and five validation individuals here; internal test remains untouched.

## Extraction, QC and protocol

Each example has two `(6,64,128)` pileups, selected read sequences, 17 scalar support features and deduplicated GRCh38 REF/ALT context. Validation extraction passed 9,981/10,000 rows (0.19% failure); train shards used for this snapshot passed their QC. No sample ID, population, GQ, AF, negative type, source filename or split is passed to the model. M0 uses images, M2 adds scalars, and M4 adds REF/ALT and read embeddings. All three models were retrained with seed 20260720, five epochs, identical rows and a threshold maximizing validation F1.

## Main results

{mainmd}

The controlled M4 F1 advantage over M2 is small. Bootstrap intervals below should not be read as final-test inference; rows are paired observations and candidate reuse limits independence.

## Paired bootstrap (1,000 row resamples)

{bootmd}

## Branch dependence

{abmd}

Zero ablations remove an encoded branch; shuffle ablations break row correspondence. Non-zero logit and prediction changes demonstrate that M4 uses the branches. A shuffled read branch can occasionally improve a finite validation realization; that is not evidence that reads are harmful.

## Subgroups

Subgroup counts and metrics are in `pairsv_train15_subgroup_metrics.csv`. Small GT 1/1 or per-person strata require caution. The same-site-negatives row is an all-negative slice, so binary precision/recall/F1 are undefined there (reported as NaN); `specificity` (TN/(TN+FP)) is the informative metric for that row: M0 {sub[(sub.model=='M0')&(sub.subgroup=='same-site negatives')].specificity.iloc[0]:.3f}, M2 {sub[(sub.model=='M2')&(sub.subgroup=='same-site negatives')].specificity.iloc[0]:.3f}, M4 {sub[(sub.model=='M4')&(sub.subgroup=='same-site negatives')].specificity.iloc[0]:.3f}. The short-deletion comparison is shown in the figure.

## Limitations and interim conclusion

Multisample dual-breakpoint models reach validation F1 around 0.80. Scalar read support is useful relative to controlled M0. Full PAIR-SV uses its additional branches and may improve short-deletion recall, but it has not yet shown a convincing overall advantage over M2. Remaining work: audit/recover all remaining shards, finish 40-person training, run three seeds, freeze threshold policy, evaluate once on the untouched five-person internal test, and perform cluster-aware inference. The final success target remains mean internal-test F1 ≥0.72 with consistent three-seed direction and multimodal dependence.
'''
(OUT/'PAIR_SV_Train15_interim_report.md').write_text(text)
styles=getSampleStyleSheet();doc=SimpleDocTemplate(str(OUT/'PAIR_SV_Train15_interim_report.pdf'),pagesize=letter);story=[]
for part in text.split('\n\n'):
 story.append(Paragraph(part.replace('# ','').replace('\n','<br/>'),styles['BodyText']));story.append(Spacer(1,8))
for n in ['architecture.png','dataset_design.png','main_comparison.png','short_deletion_recall.png','branch_ablations.png']:story.append(Image(str(FIG/n),width=450,height=220));story.append(Spacer(1,8))
doc.build(story)
