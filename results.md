# Evaluation results

| Metric | Value |
|---|---|
| Threads evaluated | 20/20 |
| Gold action items | 41 |
| Precision | 1.00 |
| Recall | 0.93 |
| F1 | 0.96 |
| Status accuracy | 1.00 |
| Deadline accuracy | 1.00 |
| Avg faithfulness | 0.99 |

Matching is one-to-one: each predicted item can satisfy at most one gold item.

| Thread | Gold | Pred | Precision | Recall | Faithfulness |
|---|---|---|---|---|---|
| thread1.txt | 2 | 2 | 1.00 | 1.00 | 1.0 |
| thread2.txt | 2 | 2 | 1.00 | 1.00 | 1.0 |
| thread3.txt | 2 | 2 | 1.00 | 1.00 | 1.0 |
| thread4.txt | 3 | 3 | 1.00 | 1.00 | 1.0 |
| thread5.txt | 4 | 4 | 1.00 | 1.00 | 1.0 |
| thread6.txt | 3 | 3 | 1.00 | 1.00 | 1.0 |
| thread7.txt | 3 | 3 | 1.00 | 1.00 | 1.0 |
| thread8.txt | 2 | 1 | 1.00 | 0.50 | 1.0 |
| thread9.txt | 1 | 1 | 1.00 | 1.00 | 1.0 |
| thread10.txt | 3 | 2 | 1.00 | 0.67 | 1.0 |
| thread11.txt | 2 | 2 | 1.00 | 1.00 | 1.0 |
| thread12.txt | 0 | 0 | 1.00 | 1.00 | 1.0 |
| thread13.txt | 2 | 1 | 1.00 | 0.50 | 1.0 |
| thread14.txt | 1 | 1 | 1.00 | 1.00 | 1.0 |
| thread15.txt | 2 | 2 | 1.00 | 1.00 | 1.0 |
| thread16.txt | 2 | 2 | 1.00 | 1.00 | 1.0 |
| thread17.txt | 1 | 1 | 1.00 | 1.00 | 1.0 |
| thread18.txt | 2 | 2 | 1.00 | 1.00 | 0.83 |
| thread19.txt | 3 | 3 | 1.00 | 1.00 | 1.0 |
| thread20.txt | 1 | 1 | 1.00 | 1.00 | 1.0 |

## Missed / extra items

- thread8.txt: MISSED Leena ['credit']
- thread10.txt: MISSED Arvind ['test']
- thread13.txt: MISSED Unassigned ['setup']
