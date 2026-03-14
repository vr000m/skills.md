---
name: rfc-finder
description: "Find and link to IETF RFCs by topic, protocol, code context, or RFC number. Trigger when the user mentions 'RFC', 'IETF', 'datatracker', a specific RFC number, 'what RFC covers X', or asks about the spec behind a protocol (WebRTC, SIP, QUIC, HTTP, TLS, STUN, TURN, ICE, SDP, RTP, RTCP, SCTP, DTLS)."
argument-hint: "<topic|protocol|RFC-number|code-snippet>"
---

# RFC Finder

Find IETF RFCs by topic, protocol, or inferred context from code. Return direct links with brief factual annotations (title, status, obsolescence relationships, which section is relevant). Do not paraphrase, summarize, or reproduce the substance of RFC content — let the link do that work.

## Usage

- `/rfc-finder WebRTC congestion control` — Search by topic
- `/rfc-finder sendNack()` — Infer protocol from code, then search
- `/rfc-finder RFC 8888` — Look up a specific RFC
- `/rfc-finder QUIC` — Find foundational and companion RFCs for a protocol family

## Step 1: Interpret the Query

Before searching, figure out what the user is actually looking for:

- **Direct topic** (e.g., "WebRTC congestion control") — search as-is
- **Code-derived** (e.g., a function named `sendNack()` or a variable `FEC_PAYLOAD_TYPE`) — infer the protocol first. `sendNack` likely relates to RTP/RTCP NACK feedback; `FEC_PAYLOAD_TYPE` likely relates to Forward Error Correction in RTP. State your inference before searching so the user can correct you if needed.
- **Broad protocol family** (e.g., "WebRTC") — identify the core/foundational RFC first, then note the key companion RFCs. Protocols like WebRTC have a whole family of specs; rank by how foundational each one is rather than listing them all flat.
- **Specific RFC number** (e.g., "RFC 8888") — look it up directly and return its metadata and link.

## Step 2: Search

Use the available web-browsing tools in the current Codex runtime to query these sources. In runtimes with the standard web tool, use `search_query` with a `domains` filter to find candidate pages, then `open` the official Datatracker or RFC Editor result directly.

1. **Primary**: `datatracker.ietf.org` — search for the topic/protocol keywords with `domains: ["datatracker.ietf.org"]`
2. **Fallback**: `rfc-editor.org` — if Datatracker does not surface a good result, search with `domains: ["rfc-editor.org"]`

Open specific Datatracker pages when you need to check draft-to-RFC status or verify details. Prefer official pages only; do not rely on secondary summaries when RFC metadata can be verified from Datatracker or RFC Editor. If live web browsing is unavailable in the current runtime, say that you cannot verify current RFC metadata and ask the user for a link or permission to browse.

Search tips:
- Use protocol-specific terminology (e.g., "RTCP feedback NACK" not "video call packet loss recovery")
- For broad topics, start with the protocol name + "overview" or "architecture"
- Check for "Obsoleted by" and "Updated by" relationships — always point the user to the current version

### Tracing Drafts to RFCs

IETF drafts frequently get renamed when they become RFCs, so a search for the draft name alone may miss the published version. When you find a relevant draft, always check whether it graduated to an RFC — and if so, link to the RFC instead. You can verify this by:

1. Opening the draft's Datatracker page (e.g., `https://datatracker.ietf.org/doc/draft-ietf-rmcat-gcc/`) and checking for a "Became RFC XXXX" banner or link
2. Searching for the draft's core topic keywords alongside "RFC" to find the published version under its new title

Some important specs never graduate to RFC status but may still be directly relevant to the user's question (e.g., Google Congestion Control / `draft-ietf-rmcat-gcc`, transport-wide congestion control / `draft-holmer-rmcat-transport-wide-cc-extensions`). When this happens:

- Include them only when they are clearly central to the query or when no published RFC covers the same work
- Clearly label them as **Internet-Draft** or **Expired Internet-Draft** based on Datatracker metadata, not ecosystem adoption claims
- Link to the Datatracker draft page, not to rfc-editor.org
- Note only source-backed facts such as draft status, expiry, and whether Datatracker shows that the work became an RFC

## Step 3: Return Results

**Always verify RFC numbers and links via actual search. Never rely on memorized RFC numbers — they may be wrong or outdated.**

Format results as a concise list. For each published RFC:

```
**RFC XXXX** — [Title](https://www.rfc-editor.org/rfc/rfcXXXX)
Status: Proposed Standard | Informational | etc.
Relevant section: Section X.Y — "Section Title" (if a specific section is clearly relevant)
Note: Obsoletes RFC YYYY / Updated by RFC ZZZZ (if applicable)
```

For relevant drafts that never became RFCs:

```
**draft-name** — [Title](https://datatracker.ietf.org/doc/draft-name/)
Status: Internet-Draft | Expired Internet-Draft
Note: No published RFC found on Datatracker for this work as of the search.
```

### Ranking

When multiple RFCs are related to the query, rank them by how foundational they are:
1. The core/defining RFC for the protocol or feature
2. Key extensions or companion specs that are commonly needed
3. Informational or experimental RFCs that provide additional context

### What NOT to Do

- Do NOT paraphrase or reproduce the substance of RFC content — brief factual annotations (status, relevance, obsolescence) are fine; explaining what the RFC argues or specifies is not
- Do NOT list every RFC tangentially related to a broad topic — pick the 3-5 most relevant
- Do NOT guess RFC numbers — always verify via search
- Do NOT link to drafts when a published RFC exists for the same work (check the draft's Datatracker page — drafts often get renamed when they become RFCs)
- Do NOT make ecosystem adoption claims unless you verified them from an authoritative source beyond Datatracker/RFC Editor and the user asked for that broader context
- DO include relevant drafts that never became RFCs when they are central to the query — see "Tracing Drafts to RFCs" above for the format

## Edge Cases

- **No results found**: Tell the user the search returned nothing. Suggest alternative search terms or ask them to clarify the protocol/topic. Do not fabricate results.
- **Invalid or non-existent RFC number**: If the user asks for a specific RFC number that doesn't exist, say so clearly. Suggest nearby RFC numbers or search by topic instead.
- **Ambiguous query**: If a term maps to multiple protocols (e.g., "flow control" could be TCP, HTTP/2, or QUIC), ask the user to narrow it down or return the top result for each protocol with a note.
- **Very old or obsoleted RFCs**: Always flag when an RFC has been obsoleted and link to the replacement. If the user specifically wants the old version, provide it but note the current version.

## Examples

**User**: "rfc-finder WebRTC congestion control"

**Response**:

Here are the key specs for WebRTC congestion control:

**draft-ietf-rmcat-gcc** — [A Google Congestion Control Algorithm for Real-Time Communication](https://datatracker.ietf.org/doc/draft-ietf-rmcat-gcc/)
Status: Expired Internet-Draft
Note: No published RFC found on Datatracker for this work as of the search.

**RFC 8836** — [Congestion Control Requirements for Interactive Real-Time Media](https://www.rfc-editor.org/rfc/rfc8836)
Status: Informational
Note: Informational RFC covering congestion control requirements for interactive real-time media.

**RFC 8888** — [RTP Control Protocol (RTCP) Feedback for Congestion Control](https://www.rfc-editor.org/rfc/rfc8888)
Status: Proposed Standard
Relevant section: Section 3 — "RTCP Feedback for Congestion Control"
Note: Defines an RTCP feedback format for congestion control.

**RFC 8698** — [Network-Assisted Dynamic Adaptation (NADA): A Unified Congestion Control Scheme for Real-Time Media](https://www.rfc-editor.org/rfc/rfc8698)
Status: Experimental
Note: Experimental RFC for a unified congestion control scheme for real-time media.

---

**User**: "rfc-finder what spec does sendNack() implement"

**Response**:

The function `sendNack()` most likely implements RTCP Generic NACK feedback, used in RTP-based media to request retransmission of lost packets.

**RFC 4585** — [Extended RTP Profile for Real-time Transport Control Protocol (RTCP)-Based Feedback (RTP/AVPF)](https://www.rfc-editor.org/rfc/rfc4585)
Status: Proposed Standard
Relevant section: Section 6.2.1 — "Generic NACK"
Note: Foundational spec for RTCP feedback messages including NACK. Updated by RFC 5506 and RFC 8108.

**RFC 5104** — [Codec Control Messages in the RTP Audio-Visual Profile with Feedback (AVPF)](https://www.rfc-editor.org/rfc/rfc5104)
Status: Proposed Standard
Note: Defines FIR, TMMBR, and other codec control messages for AVPF. (PLI is defined in RFC 4585, not here.)
