"""LP1F / LP1H form-filling pack. DRAFT: needs lawyer review."""
from .common import DRAFT_NOTICE, age_on, issue, norm, person
from .guide_lpa import CP_CHECKS, LPA_FEE
from .guides import SERVICES
from .lpa_presets import selected_wordings

FORM_SLOTS = 4  # attorneys / replacements the printed form has room for


def _people(a: dict) -> tuple[list, list, list, dict]:
    att = (a.get("attorneys") or {}).get("attorneys") or []
    rep = (a.get("replacements") or {}).get("replacement_attorneys") or []
    notify = (a.get("notify") or {}).get("people_to_notify") or []
    cp = a.get("certificate_provider") or {}
    return att, rep, notify, cp


def lpa_issues(service_id: str, a: dict, uploads_text: str = "") -> list[dict]:
    out = []
    donor = a.get("donor") or {}
    att, rep, notify, cp = _people(a)
    if donor.get("date_of_birth") and (age_on(donor["date_of_birth"]) or 0) < 18:
        out.append(issue("error", "You must be 18 or over to make an LPA."))
    for role, people in (("Attorney", att), ("Replacement attorney", rep)):
        for p in people:
            age = age_on(p.get("date_of_birth", "")) if p.get("date_of_birth") else None
            if age is not None and age < 18:
                out.append(issue("error", f"{role} {p.get('full_name')} is under 18. Attorneys must be 18 or over."))
    att_names = {norm(p.get("full_name")) for p in att if p.get("full_name")}
    rep_names = {norm(p.get("full_name")) for p in rep if p.get("full_name")}
    for n in att_names & rep_names:
        out.append(issue("error", f"{n.title()} is both an attorney and a replacement attorney. A replacement cannot also be a main attorney."))
    for p in notify:
        if norm(p.get("full_name")) in att_names | rep_names:
            out.append(issue("error", f"{p.get('full_name')} is an attorney or replacement, so cannot also be a person to notify."))
    if norm(cp.get("full_name")) and norm(cp.get("full_name")) in att_names | rep_names:
        out.append(issue("error", "Your certificate provider cannot be one of your attorneys or replacement attorneys."))
    if norm(cp.get("full_name")) and norm(cp.get("full_name")) == norm(donor.get("full_name")):
        out.append(issue("error", "You cannot be your own certificate provider."))
    if cp.get("full_name") and any(cp.get(k) is False for k, _ in CP_CHECKS):
        out.append(issue("error", "Your certificate provider does not meet every eligibility check. Please choose someone else."))
    if cp.get("full_name") and uploads_text and norm(cp["full_name"]) in norm(uploads_text):
        out.append(issue("warning", f"{cp['full_name']} is named in a document you uploaded. If they are an attorney under an earlier LPA or EPA, they should not be your certificate provider. A solicitor will check this."))
    dec = (a.get("decisions") or {}).get("decisions", "")
    if len(att) > 1 and dec == "Only one attorney":
        out.append(issue("error", "You have more than one attorney, so choose how they make decisions (section 3)."))
    if len(att) == 1 and dec and dec != "Only one attorney":
        out.append(issue("warning", "You have one attorney, so section 3 does not apply. We will leave it blank on the form."))
    if len(att) > FORM_SLOTS:
        out.append(issue("info", f"You have {len(att)} attorneys. The first {FORM_SLOTS} go in section 2; the rest go on continuation sheet 1."))
    if len(rep) > FORM_SLOTS:
        out.append(issue("info", f"You have {len(rep)} replacement attorneys. The extra ones go on continuation sheet 1."))
    if (a.get("donor") or {}).get("existing_lpa", "No") not in ("", "No"):
        out.append(issue("warning", "You told us you already have an LPA or EPA. A solicitor will check how the new LPA fits with it, and whether the old one should be revoked."))
    biz = a.get("business") or {}
    if biz.get("has_business") == "Yes":
        purpose = biz.get("purpose") or ""
        if purpose in ("Personal finances only", "Business affairs only"):
            out.append(issue("info", "You have limited this LPA to " + purpose.lower() + ". Official guidance is to make two LP1F forms if you want different attorneys or a clean split between personal and business affairs. A solicitor should check both."))
        if purpose == "Both personal and business (same attorneys)":
            out.append(issue("warning", "If you later want one attorney to deal only with the business and another only with your personal affairs, do not add that as an instruction in this LPA. LP12 says the LPA will not work if attorneys appointed jointly and severally are then told to split those roles. Make two LPAs instead."))
        if biz.get("talked_to_co_owners") == "Not yet":
            out.append(issue("warning", "You have not yet talked to co-owners, partners or fellow shareholders."))
        if biz.get("has_agreement") in ("No", "Not sure"):
            out.append(issue("warning", "A solicitor should check any partnership or shareholders' agreement before this business LPA is signed."))
    chosen = selected_wordings(service_id, a)
    if any(p.get("solicitor_review") for p in chosen):
        out.append(issue("warning", "One or more of the section 7 options you ticked needs solicitor review, including any discretionary investment or home/care restriction wording."))
    if any(p["id"] == "discretionary_investments" for p in chosen):
        out.append(issue("info", "A property and financial affairs LPA already covers making or selling investments. The extra stocks-and-shares wording is the former OPG clause about discretionary management and nominee names, which current LP12 no longer prints. A solicitor should review it."))
    if any(p["id"] in ("must_not_sell_home", "must_not_residential_care") for p in chosen):
        out.append(issue("warning", "A binding instruction about not selling your home or not moving into residential care can make the LPA hard to use. Official guidance says complicated or badly worded instructions can make an LPA unworkable."))
    return out


def _who(p: dict) -> str:
    born = f", born {p.get('date_of_birth')}" if p.get("date_of_birth") else ""
    email = f", email {p['email']}" if p.get("email") else ""
    return f"{person(p)}{born}{email}"


def build_lpa(service_id: str, a: dict, uploads: list | None = None) -> dict:
    s = SERVICES[service_id]
    form = s["form"]
    donor = a.get("donor") or {}
    att, rep, notify, cp = _people(a)
    dec = (a.get("decisions") or {})
    prefs = a.get("preferences") or {}
    reg = a.get("registration") or {}
    cont1, cont2 = [], []
    sec = []
    sec.append({"heading": f"Section 1: the donor", "paragraphs": [
        "Name: " + donor.get("full_name", ""), "Other names: " + (donor.get("other_names") or "None"),
        "Date of birth: " + donor.get("date_of_birth", ""), "Address: " + " ".join((donor.get("address") or "").split()),
        "Email: " + donor.get("email", "")]})
    sec.append({"heading": "Section 2: the attorneys", "paragraphs": [f"Attorney {i}: {_who(p)}" for i, p in enumerate(att[:FORM_SLOTS], 1)]})
    cont1 += [f"Additional attorney: {_who(p)}" for p in att[FORM_SLOTS:]]
    if len(att) > 1:
        lines = ["Tick: " + dec.get("decisions", "")]
        if dec.get("joint_decisions"):
            lines.append("Decisions to be made jointly (write on continuation sheet 2): " + dec["joint_decisions"])
            cont2.append("How attorneys make decisions (section 3): the attorneys must act jointly for these decisions and jointly and severally for all other decisions: " + dec["joint_decisions"])
    else:
        lines = ["Leave blank: you have one attorney."]
    sec.append({"heading": "Section 3: how your attorneys make decisions", "paragraphs": lines})
    sec.append({"heading": "Section 4: replacement attorneys", "paragraphs": [f"Replacement {i}: {_who(p)}" for i, p in enumerate(rep[:FORM_SLOTS], 1)] or ["None"]})
    cont1 += [f"Additional replacement attorney: {_who(p)}" for p in rep[FORM_SLOTS:]]
    if (a.get("replacements") or {}).get("replacement_instructions"):
        cont2.append("Replacement attorneys (section 4): " + a["replacements"]["replacement_instructions"])
    if service_id == "lpa_property":
        sec.append({"heading": "Section 5: when your attorneys can make decisions", "paragraphs": ["Tick: " + (a.get("when") or {}).get("when_used", "")]})
    else:
        sec.append({"heading": "Section 5: life-sustaining treatment", "paragraphs": ["Sign: " + (a.get("life_sustaining") or {}).get("life_sustaining", ""), "You sign this box in front of a witness, at the same time as section 9."]})
    sec.append({"heading": "Section 6: people to notify", "paragraphs": [person(p) for p in notify] or ["None"]})
    chosen = selected_wordings(service_id, a)
    pref_lines = [p["wording"] for p in chosen if p["section"] == "preferences"]
    inst_lines = [p["wording"] for p in chosen if p["section"] == "instructions"]
    if (prefs.get("preferences") or "").strip():
        pref_lines.append(prefs["preferences"].strip())
    if (prefs.get("instructions") or "").strip():
        inst_lines.append(prefs["instructions"].strip())
    sec7 = []
    if pref_lines:
        sec7.append("Preferences:")
        sec7.extend(pref_lines)
    else:
        sec7.append("Preferences: None")
    if inst_lines:
        sec7.append("Instructions:")
        sec7.extend(inst_lines)
    else:
        sec7.append("Instructions: None")
    if any(p.get("source_note") for p in chosen):
        sec7.append("Sources for ticked wording: " + " ".join(sorted({p["source_note"] for p in chosen})))
    sec7.append("If either is too long for the box, write 'see continuation sheet 2' and continue there.")
    sec.append({"heading": "Section 7: preferences and instructions", "paragraphs": sec7})
    if pref_lines or inst_lines:
        extra = []
        extra += [f"Preference: {w}" for w in pref_lines]
        extra += [f"Instruction: {w}" for w in inst_lines]
        if len(" ".join(pref_lines + inst_lines)) > 400:
            cont2.extend(extra)
    sec.append({"heading": "Section 8: your legal rights and responsibilities", "paragraphs": ["Read this section of the form before you sign. There is nothing to fill in."]})
    sec.append({"heading": "Section 9: your signature", "paragraphs": ["You sign and date in front of a witness who is 18 or over and is not one of your attorneys or replacements."]})
    sec.append({"heading": "Section 10: certificate provider", "paragraphs": [person(cp), "Qualifies by: " + cp.get("basis", ""), "Eligibility checks confirmed: " + ("all" if all(cp.get(k) is True for k, _ in CP_CHECKS) else "NOT all, see issues")]})
    sec.append({"heading": "Section 11: attorneys' signatures", "paragraphs": ["Each attorney and replacement signs their own copy of section 11 in front of a witness, after you and the certificate provider have signed."]})
    corr = reg.get("correspondent", "")
    sec.append({"heading": "Sections 12 to 15: registration", "paragraphs": [
        "Section 12, applicant: " + reg.get("applicant", ""),
        "Section 13, who receives the LPA: " + corr + (f" ({' '.join(reg.get('correspondent_details', '').split())})" if reg.get("correspondent_details") else ""),
        "Section 14, fee: " + reg.get("fee_reduction", "") + f". Full fee £{LPA_FEE}." + (" Fill in form LPA120 and send evidence." if str(reg.get("fee_reduction", "")).startswith("Yes") else ""),
        "Repeat application within 3 months: " + (reg.get("repeat_application") or "No"),
        "Section 15: the applicant (or each attorney applying) signs last."]})
    if cont1:
        sec.append({"heading": "Continuation sheet 1 (additional people)", "paragraphs": cont1})
    if cont2:
        sec.append({"heading": "Continuation sheet 2 (additional wording)", "paragraphs": cont2})
    if notify:
        sec.append({"heading": "Form LP3 to send before registering", "paragraphs": [f"Send LP3 to {person(p)}" for p in notify]})
    if uploads:
        sec.append({"heading": "Documents you uploaded", "paragraphs": [f"{u['filename']} ({u['kind']})" for u in uploads]})
    return {"title": f"{form} form-filling pack: " + donor.get("full_name", ""), "notice": DRAFT_NOTICE + f" This pack shows what to write in each section of the official {form} form; it is not itself the LPA.",
            "sections": sec, "next_steps": s["next_steps"], "sources": [x for st in s["steps"] for x in st.get("sources", [])]}
