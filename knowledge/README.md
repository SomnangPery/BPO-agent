# IC Agent Knowledge Folder

Put local knowledge documents here for RAG indexing.

Recommended content:
- OPPM skill sheets (converted to `.md` or `.txt`)
- SRS guidelines
- Incubation Center evaluation policies
- Rubrics and decision rules

Supported file types by default:
- `.md`
- `.txt`
- `.json`
- `.csv`

After adding files, run:

```bash
python train.py
```

or

```bash
python -m ic_agent.rag_pipeline
```
