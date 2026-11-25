"""Draft will text with a plain-English note on every clause. DRAFT WORDING: must be checked by a
solicitor before any client signs it. Not for use until a lawyer has reviewed the precedents."""
import re
from datetime import date

from .common import DRAFT_NOTICE, age_on, issue, norm, num, person
from .fields import GOV
from .guides import SERVICES


TRUST_LINKS = ("trusts", "trust_types", "trust_register")


def has_trust(tr: dict) -> bool:
    return tr.get("life_interest", "No") != "No" or tr.get("discretionary") == "Yes" or bool(tr.get("vulnerable_beneficiary"))


def _clause(clauses: list, text: str, note: str):
    clauses.append((text, note))


def _known_names(a: dict) -> set[str]:
    names = set()

    def add(value):
        if isinstance(value, dict):
            value = value.get("full_name")
        cleaned = norm(value or "")
        if cleaned:
            names.add(cleaned)

    me, fam, ex = a.get("about_you") or {}, a.get("family") or {}, a.get("executors") or {}
    add(me)
    for key in ("children", "guardians"):
        for person_ in fam.get(key) or []:
            add(person_)
    add(fam.get("replacement_guardian") or {})
    for person_ in ex.get("executors") or []:
        add(person_)
    add(ex.get("replacement_executor") or {})
    add(ex.get("digital_executor") or {})
    for gift in (a.get("gifts") or {}).get("gifts") or []:
        add(gift.get("beneficiary"))
    for person_ in (a.get("residue") or {}).get("residuary_beneficiaries") or []:
        add(person_)
    trusts = a.get("trusts") or {}
    add(trusts.get("life_tenant"))
    add(trusts.get("vulnerable_beneficiary"))
    add((a.get("extras") or {}).get("exclusion_name"))
    add((a.get("safeguards") or {}).get("couple_name"))
    return names


def _hit(low: str, *needles: str) -> bool:
    return any(needle in low for needle in needles)


def _old_will_flags(a: dict, uploads_text: str) -> list[dict]:
    text = uploads_text or ""
    if not text.strip():
        return []
    out = []
    low = text.lower()
    couple = (a.get("safeguards") or {}).get("couple") or ""
    out.append(issue(
        "warning",
        "File protection. The text read from this upload is not the will. A solicitor reads the original, or a complete copy of every page and every codicil, before a new will is signed. "
        "A photograph often drops a line, including the word “not”. Do not cross out, write on, or use correction fluid on the old will. "
        "The Institute of Professional Willwriters’ public note is that doing so can make the whole will invalid: make a new will, or a codicil for a small change, and have that signed and witnessed. "
        "Do not destroy the original. The old will applies until the new one is signed and witnessed. If the new will fails, the old one may be the last valid will, and an earlier will can still be evidence if the later will is challenged. "
        "The Law Society’s practice note on file retention (1 November 2018) treats an original the firm stores as the client’s property, and after death as the estate’s. Keep it until after the death or until it is returned. There is no fixed period. Some firms keep wills indefinitely, and some for fifty years. Ask the client before any original is destroyed, even where a later will is thought to exist. If a will is revoked, keep a copy. "
        "A new will’s revocation clause also revokes a guardianship appointment in the old will, so repeat that appointment if it is still wanted. "
        "The attendance note, not this screen, is what the file uses if instructions or execution are later questioned (Larke v Nugus) or a claim is made years later. This flag does not stop a claim.",
    ))
    if len(text.split()) < 80:
        out.append(issue("warning", "Very little text was read from this upload. Do not treat this reading as a complete copy of the will."))
    if _hit(low, "crossed out", "cross out", "tippex", "correction fluid", "handwritten", "written in the margin", "obliterat", "interlineat"):
        out.append(issue(
            "warning",
            "The upload mentions a crossing-out or a handwritten change. Wills Act 1837 section 21: an alteration made after the will was signed counts only if it was executed like a will, or the court is satisfied the words were already there. Words that are no longer apparent can be treated as revoked. Do not add to those marks. Make a new will or a codicil.",
        ))
    if "codicil" in low:
        out.append(issue(
            "warning",
            "A codicil is mentioned. Collect every codicil, not only the will. A codicil can change, confirm or revive an earlier will (Wills Act 1837 section 22). Reading the will without the codicil is not a reading of the last wishes.",
        ))
    if "joint will" in low:
        out.append(issue("warning", "The uploaded paper uses the words “joint will”. That is one document for two people. It is not a mirror will. A solicitor should read it before a new will is signed."))
    mutual = _hit(low, "mutual will", "shall not revoke", "agree not to revoke", "shall not hereafter be revoked")
    if mutual and couple.startswith("Mirror"):
        out.append(issue(
            "warning",
            "This draft is a mirror will, but the uploaded will uses mutual-will wording. A mirror will can be changed by each person, including after the first death, unless there was a separate promise. A mutual will may bind the survivor, after the first death, by a constructive trust. A will still cannot be made irrevocable. Do not sign the new will until a solicitor has compared them. The mutual wording is a warning for the file, not a finished clause to copy.",
        ))
    elif mutual:
        out.append(issue(
            "warning",
            "The uploaded will looks like a mutual will, or a promise not to revoke. A new will may conflict with that promise. While both makers are alive either can still change their mind. After the first death the survivor may not be free to change who inherits. A will still cannot be made irrevocable. Do not copy that promise into the new draft unless a solicitor has advised both people. A mirror will should say on its face that it is not mutual.",
        ))
    if couple.startswith("Mutual") and not mutual:
        out.append(issue("info", "This draft is described as mutual, but the uploaded will does not itself show a promise not to revoke. Do not treat the old will as mutual unless that promise is in it or in a separate agreement. Mutual wording is a solicitor’s warning, not a finished clause."))
    if _hit(low, "nil rate", "nil-rate", "debt and charge", "debt/charge"):
        out.append(issue("warning", "The old will looks like nil-rate-band or debt-and-charge planning. Do not copy it and do not delete it until a solicitor has decided. Transferable nil-rate band and the residence nil-rate band changed why many of these trusts were used. They can still be wanted, including on a second marriage. This screen does not make that decision."))
    if _hit(low, "step standard", "standard provisions"):
        out.append(issue("info", "The old will incorporates standard trustee provisions, often the STEP provisions. Note the edition. The second edition is often used with some clauses excluded, including the one about interest on tax. Do not drop or swap the edition without a decision on the file."))
    foreign = _hit(low, "abroad", "outside england", "outside the uk", "foreign will", "spain", "france", "property situate", "domicil")
    if foreign and "revoke" in low:
        out.append(issue("warning", "The old paper both revokes earlier wills and mentions property or a will abroad. A general revocation clause in the new will can cancel a foreign will the client meant to keep. Limit the revocation to property in England and Wales if the foreign will should stand."))
    outside = []
    if "joint tenant" in low:
        outside.append("a joint tenancy, which passes by survivorship and not by the will")
    if "pension" in low:
        outside.append("a pension, which usually follows a nomination or the scheme rules and not the will")
    if _hit(low, "death in service", "death-in-service"):
        outside.append("death-in-service benefits")
    if "policy" in low and "trust" in low:
        outside.append("a life policy written in trust")
    if outside:
        out.append(issue("warning", "The old will mentions " + "; ".join(outside) + ". Those often pass outside the will. Copying the gift into the new will may do nothing. Check the title and the nomination before the gift is repeated."))
    if _hit(low, "if i do not return", "if i should not return", "only if i die", "this will shall take effect only", "should i die on"):
        out.append(issue("warning", "The old will may be conditional. If the condition was not met, it may never have taken effect. Do not treat it as the last will until a solicitor has read the condition."))
    if _hit(low, "secret trust", "half secret", "half-secret") or ("i have told" in low and "wish" in low):
        out.append(issue("warning", "There may be a secret or half-secret trust, or a private instruction beside the will. Ask. Do not write the secret into the new will. A letter of wishes is not the will and should not be incorporated into it."))
    if _hit(low, "my wife", "my husband", "my spouse", "civil partner") and _hit(low, "28 days", "twenty-eight days", "thirty days", "30 days", "one calendar month"):
        out.append(issue("info", "The old will has a survivorship period and a gift to a spouse or civil partner. If the survivor dies inside that period the gift fails, and the spouse exemption from Inheritance Tax can be lost. A solicitor decides whether to keep that period. This is a flag, not a rewrite."))
    if _hit(low, "former wife", "former husband", "ex-wife", "ex-husband", "decree absolute", "dissolved civil"):
        out.append(issue("warning", "A divorce, or the end of a civil partnership, does not revoke the whole will. Wills Act 1837 sections 18A and 18C treat the former spouse or civil partner as having died, so their gifts and appointments fail and the rest of the will stands. A later marriage or civil partnership usually revokes a will unless it was made in expectation of that marriage or partnership (sections 18 and 18B)."))
    if _hit(low, "contemplation of marriage", "expecting to marry", "in expectation of"):
        out.append(issue("info", "The old will says it was made in expectation of a marriage or civil partnership. Check that it names the person they in fact married. If it does not match, the marriage may have revoked it."))
    if _hit(low, "actual military service", "on active service", "mariner", "at sea"):
        out.append(issue("info", "This may be a privileged will (Wills Act 1837 section 11). A soldier on actual military service, or a mariner or seaman at sea, can make an informal will and can be under 18. Do not assume an informal note is invalid."))
    if _hit(low, "list of gifts", "which i shall", "to be found with", "memorandum which", "set out in a letter"):
        out.append(issue("warning", "The old will may try to incorporate a list that did not exist when it was signed. A document is part of the will only if the will identifies it and it already existed. A list written later is usually not part of the will. Do not staple a new list to the old will."))
    known = _known_names(a)
    found = []
    for match in re.finditer(r"\b(?:appoint|give|bequeath|leave|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", text):
        name = norm(match.group(1))
        if name and name not in known and name not in found and name not in {"my executor", "my trustees", "the residue"}:
            found.append(name)
    for name in found[:5]:
        out.append(issue("warning", f"The uploaded will mentions “{name.title()}” in a gift or an appointment. They are not named in this new draft. Check that leaving them out is intended. The old will still applies until the new one is signed and witnessed. If they are left out, keep the reasons in a signed statement off the will. A gift to a witness, or to a witness’s spouse or civil partner, is void (Wills Act 1837 section 15); the rest of the will stands."))
    excluded = (a.get("extras") or {}).get("exclusion_name") or ""
    if excluded and norm(excluded) in norm(text):
        out.append(issue("warning", f"The uploaded will names {excluded}, who this draft leaves out or treats differently. That change can be challenged under the Inheritance (Provision for Family and Dependants) Act 1975. Keep the reasons in a signed statement, off the will. The statement does not stop a claim."))
    return out


def will_issues(a: dict, uploads_text: str = "") -> list[dict]:
    out = []
    me, fam, ex = a.get("about_you") or {}, a.get("family") or {}, a.get("executors") or {}
    res, tr, ext = a.get("residue") or {}, a.get("trusts") or {}, a.get("extras") or {}
    if me.get("date_of_birth") and (age_on(me["date_of_birth"]) or 0) < 18:
        out.append(issue("error", "You must be 18 or over to make a will (except some members of the armed forces on active service)."))
    if me.get("domicile") and me["domicile"] != "England or Wales":
        out.append(issue("warning", "Your permanent home is outside England and Wales. A solicitor must check which law applies before you rely on this will."))
    if str(me.get("assets_abroad", "")).startswith("Yes"):
        out.append(issue("warning", "You own assets abroad. A solicitor will check whether you need a separate will there and that the wills do not revoke each other."))
    minors = [c for c in fam.get("children") or [] if c.get("date_of_birth") and (age_on(c["date_of_birth"]) or 99) < 18]
    if minors and not fam.get("guardians"):
        out.append(issue("warning", "You have children under 18 but have not named guardians."))
    if sum(num(p.get("share")) for p in res.get("residuary_beneficiaries") or []) <= 0 and res.get("residuary_beneficiaries"):
        out.append(issue("error", "Give at least one residuary beneficiary a share above 0."))
    for g in (a.get("gifts") or {}).get("gifts") or []:
        if g.get("type") == "A gift to charity" and not g.get("charity_number"):
            out.append(issue("warning", f"Add the registered charity number for {g.get('beneficiary')} so the gift cannot fail."))
    exec_names = {norm(p.get("full_name")) for p in ex.get("executors") or []}
    if ext.get("exclude_person") == "Yes":
        out.append(issue("warning", "You are leaving someone out who may expect to inherit. A solicitor must review this; it can be challenged under the Inheritance (Provision for Family and Dependants) Act 1975."))
        if norm(ext.get("exclusion_name")) in exec_names:
            out.append(issue("warning", "The person you are leaving out is also an executor. Please check this is what you want."))
    if has_trust(tr):
        out.append(issue("info", "Your will includes a trust. Your solicitor will check the trust wording and its tax effect with you. GOV.UK guidance: " + GOV["trusts"]["url"]))
    biz = a.get("business") or {}
    owns = biz.get("owns_business") == "Yes" or tr.get("business_property") == "Yes"
    if owns:
        out.append(issue("info", "Your will mentions business, farm or company assets. A solicitor must draft the gift and check Inheritance Tax Business Relief, including the rules for deaths on or after 6 April 2026. This is not legal advice."))
        if biz.get("talked_to_co_owners") == "Not yet":
            out.append(issue("warning", "You have not yet talked to co-owners, partners or fellow shareholders about what should happen to the business."))
        if biz.get("has_agreement") in ("No", "Not sure"):
            out.append(issue("warning", "A solicitor should check whether a partnership or shareholders' agreement affects who can inherit or run the business."))
    safe = a.get("safeguards") or {}
    if safe.get("couple", "").startswith("Mutual"):
        out.append(issue("warning", "These are described as mutual wills. After the first death the survivor may not be free to change the will. A solicitor must advise both people before anyone signs. A mirror will does not do this. The wording below is a warning for the file, not a finished clause."))
    elif safe.get("couple", "").startswith("Mirror"):
        out.append(issue("info", "Mirror wills can each be changed, including after the other has died, unless a separate promise was made. Neither person is bound to leave their will as it is. The draft says on its face that it is not a mutual will."))
    elif safe.get("couple") == "Not sure":
        out.append(issue("warning", "It is not clear whether this is one will, a mirror will, or a mutual will. Do not finish it until that is chosen."))
    if safe.get("capacity") != "No reason to doubt it" and safe.get("doctor") == "Not yet":
        out.append(issue("warning", "The golden rule: ask a doctor to examine, apply Banks v Goodfellow, and write a note before this will is signed. Do not delay so long that the will is never made."))
    if safe.get("seen_alone") and safe.get("seen_alone") != "Yes":
        out.append(issue("warning", "Instructions should be taken with the client alone. See them without the person who benefits before the will is signed."))
    if safe.get("drafter_benefits") == "Yes" and safe.get("independent_advice") != "Yes":
        out.append(issue("warning", "SRA wills guidance (25 November 2019) and paragraph 6.1 of the Code: a gift of significant value to the will writer, a solicitor, their family or an employee needs independent advice first. If the client refuses, the drafter usually has to stop acting. A parent leaving the estate equally to their children, including a solicitor child, can be an exception. Record which it is. This flag does not decide the conflict."))
    elif safe.get("drafter_benefits") == "Yes":
        out.append(issue("info", "A gift to the drafter or their family is on the file, and independent advice is recorded. Keep that advice with the will."))
    out.extend(_old_will_flags(a, uploads_text))
    if ext.get("exclude_person") == "Yes" and not (ext.get("exclusion_reason") or "").strip():
        out.append(issue("warning", "Someone is left out and no statement of reasons has been written. Keep the reasons off the will, in a signed statement. The statement does not stop a 1975 Act claim."))
    return out


def build_will(_, a: dict, uploads: list | None = None) -> dict:
    me, fam, ex = a.get("about_you") or {}, a.get("family") or {}, a.get("executors") or {}
    gifts = (a.get("gifts") or {}).get("gifts") or []
    res, tr, ext = a.get("residue") or {}, a.get("trusts") or {}, a.get("extras") or {}
    safe = a.get("safeguards") or {}
    c: list = []
    if me.get("assets_abroad") == "Yes, and I have a separate will there":
        _clause(c, f"I, {person(me)}, revoke all my earlier wills and codicils so far as they relate to my property in England and Wales, and declare this to be my last will, which deals only with that property.",
                "Cancels earlier wills for your property here but keeps your foreign will for assets abroad.")
    else:
        _clause(c, f"I, {person(me)}, revoke all my earlier wills and codicils and declare this to be my last will.", "Cancels any earlier will so there is no confusion about which applies.")
    other = safe.get("couple_name") or "the other person"
    if str(safe.get("couple") or "").startswith("Mirror"):
        _clause(c, f"Although this will is in similar terms to the will of {other}, we have agreed that either of us can change or revoke our own will at any time, including after the other has died. This will is not a mutual will.",
                "Society of Will Writers practice: say on the face of a mirror will that each person can change it, so it is not later treated as a mutual will.")
    elif str(safe.get("couple") or "").startswith("Mutual"):
        _clause(c, f"[For solicitor drafting] {me.get('full_name') or 'The client'} and {other} have asked about mutual wills. Do not use a binding clause unless both have been advised that, after the first death, the survivor may hold what they inherit on a constructive trust and may not be free to change who benefits. A will cannot be made irrevocable. A later marriage can still revoke it. A mirror will, sometimes with a life interest, is usually what a couple wants instead.",
                "This is a warning for the file, not a finished mutual-will clause. Mutual wills are rarely appropriate.")
    if me.get("expecting_marriage") == "Yes" and me.get("partner_name"):
        _clause(c, f"I make this will expecting to marry or form a civil partnership with {me['partner_name']}, and I intend that this will shall not be revoked by that marriage or civil partnership.",
                "Normally marriage cancels a will. This stops that happening for your planned marriage.")
    executors = ex.get("executors") or []
    _clause(c, f"I appoint {'; '.join(person(p) for p in executors)} to be my executor{'s' if len(executors) > 1 else ''} and trustee{'s' if len(executors) > 1 else ''} (my trustees).",
            "Names the people who will deal with your estate and look after any trust.")
    rep = ex.get("replacement_executor") or {}
    if rep.get("full_name"):
        _clause(c, f"If any executor named above dies before me, or is unable or unwilling to act, I appoint {person(rep)} in their place.", "A back-up if an executor cannot act.")
    if ex.get("professional_executor") == "Yes":
        _clause(c, "Any executor or trustee who is a solicitor, accountant or other professional may charge for work done by them or their firm in connection with my estate, including work a lay executor could do.",
                "Lets a professional executor be paid. Without it they could only claim expenses.")
    dig = ex.get("digital_executor") or {}
    if dig.get("full_name"):
        _clause(c, f"I appoint {person(dig)} as my digital executor to deal with my digital assets and online accounts, acting under the direction of my executors, and I authorise my executors to give them access to the information they need.",
                "Someone to close or memorialise online accounts and save photos and files.")
    guardians = fam.get("guardians") or []
    if guardians:
        _clause(c, f"If no person with parental responsibility for my children survives me, I appoint {'; '.join(person(p) for p in guardians)} to be the guardian{'s' if len(guardians) > 1 else ''} of any of my children who are under 18.",
                "Chooses who looks after your children if no parent with parental responsibility is alive.")
        rg = fam.get("replacement_guardian") or {}
        if rg.get("full_name"):
            _clause(c, f"If any guardian named above dies before me or is unable or unwilling to act, I appoint {person(rg)} as guardian in their place.", "A back-up guardian.")
    for g in gifts:
        kind, what, who = g.get("type", "An item"), g.get("gift", ""), g.get("beneficiary", "")
        lapse = " If they die before me, the gift passes to their children who survive me, equally." if g.get("if_they_die") == "Their children receive it" else ""
        if kind == "A gift to charity":
            num_ = f" (registered charity number {g['charity_number']})" if g.get("charity_number") else ""
            _clause(c, f"I give {what} to {who}{num_} for its general purposes. The receipt of its treasurer or other proper officer is a full discharge to my trustees. If it has merged or changed its name, the gift goes to the body that has taken over its work.",
                    "A charity gift. It is free of Inheritance Tax, and the merger wording stops it failing if the charity changes.")
        elif kind == "A sum of money":
            _clause(c, f"I give {what} to {who}, if they survive me, free of inheritance tax.{lapse}", "A cash gift, paid before the rest of your estate is shared out.")
        elif kind == "A property or my share of it":
            _clause(c, f"I give {what} to {who}, if they survive me, free of inheritance tax but subject to any mortgage or charge secured on it.{lapse}", "A gift of property. Any mortgage on it passes with it.")
        elif kind == "My pet, with money for its care":
            money = f" together with £{num(g.get('pet_money')):,.0f} for its care, which I wish (without creating a trust) to be used for that purpose" if g.get("pet_money") else ""
            _clause(c, f"I give {what} to {who}, if they survive me and are willing to look after it,{money}.", "Makes sure your pet is looked after.")
        else:
            _clause(c, f"I give {what} to {who}, if they survive me, free of inheritance tax.{lapse}", "A gift of a particular item.")
    if ext.get("loans_forgiven"):
        _clause(c, f"I release the following debts owed to me, with any interest, at my death: {ext['loans_forgiven']}.", "Cancels loans you made so the borrower does not have to repay your estate.")
    li = tr.get("life_interest", "No")
    if li != "No" and tr.get("life_tenant"):
        subject = "my interest in the property which is my main residence at my death (and any property bought to replace it)" if "home" in li else "my residuary estate"
        _clause(c, f"My trustees shall hold {subject} on trust to allow {tr['life_tenant']} to live in it or receive the income from it for the rest of their life, and then to hold it as part of my residuary estate for the beneficiaries below. My trustees may sell it and buy a replacement with the life tenant's consent.",
                "A life interest trust: your partner can stay in the home for life, and its value is protected for your children afterwards.")
    people = res.get("residuary_beneficiaries") or []
    total = sum(num(p.get("share")) for p in people) or 1
    shares = "; ".join(f"{p.get('full_name')} ({p.get('relationship') or 'beneficiary'}): {num(p.get('share')) / total:.0%}" for p in people)
    age = res.get("inherit_age") or "18"
    if tr.get("discretionary") == "Yes":
        _clause(c, "My trustees shall hold my residuary estate (everything left after paying my debts, funeral and testamentary expenses and the gifts above) on discretionary trust for the following people, their spouses or civil partners and descendants, and any charity: "
                + ", ".join(p.get("full_name", "") for p in people) + ". My trustees may pay or apply income and capital to any of them in such shares and at such times as they decide within the trust period of 125 years, and I ask them to take my letter of wishes into account.",
                "A discretionary trust: your trustees decide who benefits and when, guided by your letter of wishes. It can protect against divorce, bankruptcy and tax.")
    else:
        _clause(c, f"I give the rest of my estate, after payment of my debts, funeral and testamentary expenses and the gifts above (my residuary estate), to my trustees to hold on trust to sell or keep, and to divide among the following people who survive me by 28 days and reach the age of {age}, in these shares: {shares}.",
                f"Shares out everything else. Beneficiaries must outlive you by 28 days and inherit outright at {age}.")
        if res.get("substitution", "").startswith("Their children"):
            _clause(c, f"If any of them dies before me, or within 28 days of me, or before reaching {age}, leaving children who survive me, those children who reach {age} take equally the share their parent would have taken.", "If a beneficiary dies first, their children take their share.")
        else:
            _clause(c, f"If any of them dies before me, or within 28 days of me, or before reaching {age}, their share is added to the shares of the others in proportion.", "If a beneficiary dies first, the others share their part.")
    if tr.get("vulnerable_beneficiary"):
        _clause(c, f"Any share of my estate for {tr['vulnerable_beneficiary']} shall not be paid to them outright but held by my trustees on discretionary trust for their benefit during their lifetime, so as to protect their entitlement to means-tested benefits and care, with the remainder passing as part of my residuary estate.",
                "A vulnerable person's trust protects someone disabled or on means-tested benefits.")
    biz = a.get("business") or {}
    owns = biz.get("owns_business") == "Yes" or tr.get("business_property") == "Yes"
    details = (biz.get("business_details") or tr.get("business_details") or "").strip()
    if owns and details:
        kind = biz.get("business_type") or "business or agricultural property"
        extra = []
        if biz.get("separate_planning") == "Yes":
            extra.append("The client has asked a solicitor to consider a separate gift, will or trust for these assets, including Inheritance Tax Business Relief.")
        if biz.get("has_agreement"):
            extra.append(f"Partnership or shareholders' agreement: {biz['has_agreement']}.")
        note = (
            "This is a placeholder only. A solicitor must draft the gift and check Inheritance Tax Business Relief "
            "(GOV.UK: a business or interest in a business, and shares in an unlisted company, may qualify for 100% relief "
            "if the conditions are met, usually including two years of ownership. For deaths on or after 6 April 2026, "
            "100% relief is capped at £2.5 million of qualifying business or agricultural property, with 50% relief on the rest). "
            "This is not legal advice."
        )
        _clause(c, f"[For solicitor drafting] {kind}: {details}. " + " ".join(extra), note)
    if res.get("ultimate_beneficiary"):
        _clause(c, f"If none of the gifts of my residuary estate take effect, I give my residuary estate to {res['ultimate_beneficiary']}.", "A last back-up so your estate does not pass under the intestacy rules.")
    if ext.get("lifetime_gifts") == "Yes":
        _clause(c, "Any substantial gift I made in my lifetime to a residuary beneficiary, or to their parent, shall be taken into account in calculating their share, unless I said otherwise in writing when making it.",
                "Makes the shares fair where you have already given someone a lot during your life.")
    else:
        _clause(c, "No gift I made in my lifetime is to be taken into account in calculating any share of my estate.", "Lifetime gifts do not reduce anyone's share.")
    _clause(c, f"My trustees have the powers given to trustees by law, including the Trustee Act 2000, and the statutory powers of maintenance and advancement (sections 31 and 32 of the Trustee Act 1925) as amended, which may be used for any beneficiary under {age}. They may appropriate assets in or towards any share without the consent of any beneficiary.",
            "Gives your trustees practical powers to invest, use money for young beneficiaries and transfer assets rather than selling them.")
    if ext.get("digital_assets_location"):
        _clause(c, f"A list of my digital assets and online accounts is kept at: {ext['digital_assets_location']}. It is not part of this will and contains no passwords.", "Tells your executors where to find your list of online accounts.")
    fw = ext.get("funeral_wishes")
    wishes = []
    if fw and fw != "No preference":
        wishes.append({"Burial": "I would like to be buried.", "Cremation": "I would like to be cremated.", "Natural or woodland burial": "I would like a natural or woodland burial."}.get(fw, ""))
    if ext.get("funeral_notes"):
        wishes.append(ext["funeral_notes"].strip())
    if ext.get("organ_donation") and ext["organ_donation"] != "No preference":
        wishes.append(ext["organ_donation"] + ".")
    if wishes:
        _clause(c, "I express the following wishes, which are not binding on my executors: " + " ".join(w for w in wishes if w), "Funeral and organ donation wishes. They are not legally binding, but executors usually follow them.")
    sections = [{"heading": "Last will and testament of " + me.get("full_name", ""), "paragraphs": [f"{i}. {t}" for i, (t, _) in enumerate(c, 1)],
                 "notes": [f"{i}. {n}" for i, (_, n) in enumerate(c, 1)]}]
    sections.append({"heading": "Commentary: what each clause does (not part of the will)", "paragraphs": [f"{i}. {n}" for i, (_, n) in enumerate(c, 1)]})
    sections.append({"heading": "Signature", "paragraphs": [
        "Signed by the testator in our presence, both present at the same time, and then signed by each of us in the testator's presence.",
        "Testator signature: ______________________   Date: ____________",
        "Witness 1 signature, full name, address and occupation: ______________________________________________",
        "Witness 2 signature, full name, address and occupation: ______________________________________________"]})
    if ext.get("letter_of_wishes") or fam.get("guardian_wishes"):
        sections.append({"heading": "Letter of wishes (separate document, not part of the will)", "paragraphs": [x for x in (fam.get("guardian_wishes"), ext.get("letter_of_wishes")) if x]})
    if ext.get("exclude_person") == "Yes":
        sections.append({"heading": "Statement of reasons (separate document, not part of the will)", "paragraphs": [
            f"I have decided not to provide for {ext.get('exclusion_name', '')} in my will for these reasons: {ext.get('exclusion_reason', '')}",
            f"Signed: ______________________   Date: {date.today().strftime('%d %B %Y')}"]})
    if has_trust(tr):
        sections.append({"heading": "Trust guidance from GOV.UK (not part of the will)", "paragraphs": [
            f"{GOV[k]['title']}: {GOV[k]['url']}" for k in TRUST_LINKS]})
    if uploads:
        sections.append({"heading": "Documents you uploaded", "paragraphs": [f"{u['filename']} ({u['kind']})" for u in uploads]})
    s = SERVICES["will"]
    return {"title": "Will: " + me.get("full_name", ""), "notice": DRAFT_NOTICE, "sections": sections, "next_steps": s["next_steps"], "sources": [x for st in s["steps"] for x in st.get("sources", [])]}
