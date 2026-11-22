import pandas as pd
import streamlit as st
import cache
from thread_parser import parse_thread, format_for_llm
from chunker import summarize_long, thread_tokens, chunk_by_tokens
from verifier import faithfulness_report, Verdict
from privacy import mask_messages
from extractor import ThreadResult

st.set_page_config(page_title="Email Thread Summarizer", layout="wide")
st.title("📧 Email Thread Summarizer & Action Tracker")

with st.sidebar:
    st.header("Settings")
    use_mask = st.checkbox("Mask PII before sending to API", True)
    use_verify = st.checkbox("Run faithfulness check", True)
    use_cache = st.checkbox("Demo cache (saves results to disk)", False)
    chunk_tokens = st.slider("Chunk size (tokens)", 500, 20000, 6000, 500)
    single_limit = st.slider("Single-pass limit (tokens)", 0, 100000, 30000, 1000)
    st.caption("Threads at or below the single-pass limit are summarised in one call; "
               "longer ones are chunked, extracted per chunk, then reconciled.")
    st.caption("With the demo cache off, threads are processed in memory and never stored.")

st.write("Paste a thread, separating messages with a line of `======`")
uploaded = st.file_uploader("...or upload a .txt file", type="txt")

if "thread_text" not in st.session_state:
    st.session_state.thread_text = ""
if st.button("Load sample thread"):
    st.session_state.thread_text = open("data/thread1.txt", encoding="utf-8").read()
if uploaded:
    st.session_state.thread_text = uploaded.read().decode("utf-8")

raw = st.text_area("Thread", key="thread_text", height=250)

if st.button("Summarise", type="primary"):
    if not raw.strip():
        st.error("Paste or load a thread first.")
        st.stop()

    parsed = parse_thread(raw)
    total = thread_tokens(parsed)
    n_chunks = len(chunk_by_tokens(parsed, chunk_tokens)) if total > single_limit else 1
    st.caption(f"{len(parsed)} messages, ~{total} tokens → "
               + ("single pass" if n_chunks == 1 else f"{n_chunks} chunks + reconciliation"))

    ck = cache.make_key(raw, use_mask, f"{chunk_tokens}-{single_limit}")
    cached = cache.load(ck) if use_cache else None

    if cached:
        result = ThreadResult(**cached["result"])
        report = cached["report"]
        if report:
            report["unsupported"] = [Verdict(**v) for v in report["unsupported"]]
        st.success("⚡ Loaded from demo cache (no API call)")
    else:
        messages = parsed
        masker = None
        if use_mask:
            messages, masker = mask_messages(messages)

        with st.expander(f"What the API sees ({len(messages)} messages)"):
            st.code(format_for_llm(messages)[:3000])

        with st.spinner("Summarising..."):
            result = summarize_long(messages, chunk_tokens, single_limit)

        report = None
        if use_verify:
            with st.spinner("Checking faithfulness..."):
                report = faithfulness_report(result, messages, format_for_llm(messages))

        if masker:
            result = ThreadResult(**masker.restore_obj(result.model_dump()))
            if report:
                report["unsupported"] = [
                    Verdict(claim=masker.restore(v.claim), supported=v.supported,
                            reason=masker.restore(v.reason))
                    for v in report["unsupported"]]
                report["bad_quotes"] = [masker.restore(t) for t in report["bad_quotes"]]

        if use_cache:
            saved = None
            if report:
                saved = dict(report)
                saved["unsupported"] = [v.model_dump() for v in report["unsupported"]]
            cache.save(ck, {"result": result.model_dump(), "report": saved})

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Summary")
        st.write(result.summary)
        if result.decisions:
            st.subheader("Decisions")
            for d in result.decisions:
                st.markdown(f"- {d}")
    with col2:
        if report:
            st.metric("Faithfulness", f"{report['faithfulness_score']:.0%}")
            st.caption(f"Quotes verified: {report['quote_match']}")
            st.caption(f"Claims supported: {report['claims_supported']}")

    st.subheader("Action items")
    if result.action_items:
        df = pd.DataFrame([{
            "Task": a.task, "Owner": a.owner, "Deadline": a.deadline,
            "Status": a.status, "Source msg": a.source_msg_id,
            "Evidence": a.supporting_quote,
        } for a in result.action_items])
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No action items found.")

    if report and (report["unsupported"] or report["bad_quotes"]):
        st.warning("Some items could not be verified:")
        for v in report["unsupported"]:
            st.markdown(f"- ❌ {v.claim} — *{v.reason}*")
        for t in report["bad_quotes"]:
            st.markdown(f"- ❌ Quote mismatch: {t}")
