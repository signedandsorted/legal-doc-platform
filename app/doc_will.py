"""Draft will text with a plain-English note on every clause. DRAFT WORDING: must be checked by a
solicitor before any client signs it. Not for use until a lawyer has reviewed the precedents."""
from datetime import date

from .common import DRAFT_NOTICE, age_on, issue, norm, num, person
from .fields import GOV
from .guides import SERVICES


TRUST_LINKS = ("trusts", "trust_types", "trust_register")


def has_trust(tr: dict) -> bool:
    return tr.get("life_interest", "No") != "No" or tr.get("discretionary") == "Yes" or bool(tr.get("vulnerable_beneficiary"))


def _clause(clauses: list, text: str, note: str):
    clauses.append((text, note))


def will_issues(a: dict) -> list[dict]:
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
    return out


def build_will(_, a: dict, uploads: list | None = None) -> dict:
    me, fam, ex = a.get("about_you") or {}, a.get("family") or {}, a.get("executors") or {}
    gifts = (a.get("gifts") or {}).get("gifts") or []
    res, tr, ext = a.get("residue") or {}, a.get("trusts") or {}, a.get("extras") or {}
    c: list = []
    if me.get("assets_abroad") == "Yes, and I have a separate will there":
        _clause(c, f"I, {person(me)}, revoke all my earlier wills and codicils so far as they relate to my property in England and Wales, and declare this to be my last will, which deals only with that property.",
                "Cancels earlier wills for your property here but keeps your foreign will for assets abroad.")
    else:
        _clause(c, f"I, {person(me)}, revoke all my earlier wills and codicils and declare this to be my last will.", "Cancels any earlier will so there is no confusion about which applies.")
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
