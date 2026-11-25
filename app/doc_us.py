"""United States drafts. Signing follows the state the client named. Not a UK will."""
from datetime import date

from .guide_us import US_HEALTH, US_POA, US_PROBATE, US_TRUST, US_WILL
from .us_states import SOURCES, execution, minimum_age, property_note

_NEXT = {item["id"]: item["next_steps"] for item in (US_WILL, US_TRUST, US_POA, US_HEALTH, US_PROBATE)}


def issue(level: str, message: str) -> dict:
    return {"level": level, "message": message}


def _step(answers: dict, sid: str) -> dict:
    return answers.get(sid) or {}


def _name(block) -> str:
    if isinstance(block, dict):
        return (block.get("full_name") or "").strip()
    return ""


def _state_of(about: dict) -> str:
    return (about.get("state") or "").strip()


def _age_issue(about: dict) -> list[dict]:
    state = _state_of(about)
    raw = about.get("date_of_birth") or ""
    if not state or not raw:
        return []
    try:
        born = date.fromisoformat(raw)
    except ValueError:
        return [issue("warning", "The date of birth could not be read.")]
    years = date.today().year - born.year - ((date.today().month, date.today().day) < (born.month, born.day))
    need = minimum_age(state)
    if years < need:
        return [issue("error", f"In {state} you generally need to be {need} to make this document. The date of birth entered is under that age.")]
    return []


def us_issues(service_id: str, answers: dict, uploads_text: str = "") -> list[dict]:
    about = _step(answers, "about")
    out = _age_issue(about)
    state = _state_of(about)
    if state == "Louisiana" and service_id in ("us_will", "us_trust"):
        out.append(issue("warning", "Louisiana does not use this kind of will. A notary there must prepare a notarial testament, or you must write the whole testament in your handwriting, date it and sign it. Do not sign this printout as the testament."))
    if service_id == "us_trust":
        gifts = _step(answers, "gifts")
        if gifts.get("funded") is not True:
            out.append(issue("warning", "A revocable trust avoids probate only for assets transferred into it. Nothing has been transferred by answering these questions."))
    if service_id == "us_probate" and about.get("has_will") == "There may be one, I have not found it":
        out.append(issue("warning", "Search the house, the safe-deposit box and the lawyer the person used before you tell the court there is no will."))
    if uploads_text and "trust & will" in uploads_text.lower():
        out.append(issue("info", "An uploaded plan from another service is not this draft. Read it before you sign a new one, and do not destroy the old original."))
    return out


def _people_lines(people: dict) -> list[str]:
    first = _name(people.get("primary")) or "the person I name at the end of this paragraph"
    backup = _name(people.get("backup"))
    lines = [f"I name {first}."]
    if backup:
        lines.append(f"If {first} cannot act, I name {backup}.")
    if people.get("guardian"):
        lines.append(f"If I have a child under 18, I name {people['guardian']} as guardian of the person. A court still has to appoint them.")
    return lines


def _signing(state: str, title: str) -> dict:
    lines = execution(state or "your state")
    lines.append("Sign the paper original. Do not rely on a typed name on this screen.")
    return {"heading": f"How to sign — {title}", "paragraphs": lines, "notes": ["These are signing instructions. They are not the signed document."]}


def build_us(service_id: str, answers: dict, uploads=None) -> dict:
    about = _step(answers, "about")
    people = _step(answers, "people")
    gifts = _step(answers, "gifts")
    state = _state_of(about) or "the state I named"
    who = (about.get("full_name") or about.get("your_name") or "the person named below").strip()
    married = about.get("marital") in ("Married", "Domestic partnership or civil union")
    prop = property_note(state, married)
    sections = []
    if service_id == "us_probate":
        return _probate(about)
    if service_id == "us_will":
        sections = _will_sections(who, about, people, gifts, state, prop)
        title = f"Last will and testament of {who}"
        notice = f"Draft for {state}. It is not valid until it is signed the way that state requires. It does not avoid probate."
    elif service_id == "us_trust":
        sections = _trust_sections(who, about, people, gifts, state, prop)
        title = f"Revocable living trust of {who}"
        notice = f"Draft for {state}. You can change or cancel it while you are able. It avoids probate only for assets you later transfer into it."
    elif service_id == "us_poa":
        sections = _poa_sections(who, about, people, state)
        title = f"Durable financial power of attorney of {who}"
        notice = f"Draft for {state}. It is not a healthcare directive and it is not a UK lasting power of attorney."
    else:
        sections = _health_sections(who, about, people, state)
        title = f"Advance healthcare directive of {who}"
        notice = f"Draft for {state}. It is not a POLST or MOLST. A clinician signs those."
    sections.append(_signing(state, title))
    sections.append({
        "heading": "Commentary: what this is, and what it is not",
        "paragraphs": [
            "This is a United States document for the state named above. It is not an England and Wales will, lasting power of attorney, or probate application.",
            "A lawyer in that state is optional. Paying for this download does not buy a lawyer.",
            "Beneficiary forms on retirement accounts and life insurance win over this document unless those forms name this plan.",
        ],
    })
    return {"title": title, "notice": notice, "sections": sections, "next_steps": _NEXT.get(service_id, []), "sources": list(SOURCES)}


def _will_sections(who, about, people, gifts, state, prop) -> list[dict]:
    gift_lines = []
    for item in gifts.get("gifts") or []:
        if item.get("item") and item.get("to"):
            gift_lines.append(f"I give {item['item']} to {item['to']}.")
    if not gift_lines:
        gift_lines = ["I make no separate gift. Everything that passes under this will goes as the residue."]
    family = []
    if about.get("spouse"):
        family.append(f"My spouse or partner is {about['spouse']}.")
    kids = [c.get("full_name") for c in (about.get("children") or []) if c.get("full_name")]
    family.append("My children are " + ", ".join(kids) + "." if kids else "I have not named a child on this will.")
    if prop:
        family.append(prop)
    residue = gifts.get("residue") or "the people I name in the residue clause when I sign"
    extra = []
    if gifts.get("pets"):
        extra.append("Pets: " + gifts["pets"])
    if gifts.get("digital"):
        extra.append("Digital accounts: " + gifts["digital"] + " This does not give the person the password. It asks the executor to use the access the state allows.")
    sections = [
        {"heading": "Revocation", "paragraphs": [f"I, {who}, of {about.get('county', 'the county I named')}, {state}, revoke my earlier wills and codicils. I do not revoke beneficiary forms on retirement accounts or life insurance by this sentence."], "notes": ["A new will replaces the old one only once this one is validly signed."]},
        {"heading": "Family", "paragraphs": family, "notes": ["A spouse in a community-property state may already own half of property acquired during the marriage."]},
        {"heading": "Executor", "paragraphs": ["I name this executor to administer my estate. The probate court still appoints them."] + _people_lines(people), "notes": ["A will does not avoid probate."]},
        {"heading": "Gifts", "paragraphs": gift_lines, "notes": ["If a gift fails, it falls into the residue."]},
        {"heading": "Residue", "paragraphs": [f"I give the rest of my estate to {residue}."], "notes": ["What is left after debts, taxes and the gifts above."]},
    ]
    if extra:
        sections.append({"heading": "Other wishes", "paragraphs": extra, "notes": ["Wishes about a pet or a digital account are instructions. A court may still have to approve them."]})
    return sections


def _trust_sections(who, about, people, gifts, state, prop) -> list[dict]:
    trustee = _name(people.get("primary")) or who
    lines = [
        f"I, {who}, of {about.get('county', '')}, {state}, create this revocable trust. While I am able, I am the trustee and the beneficiary.",
        f"If I cannot act, {trustee} acts as successor trustee." if trustee != who else "I will name a successor trustee before I sign.",
    ]
    if _name(people.get("backup")):
        lines.append(f"If the successor cannot act, {_name(people.get('backup'))} acts.")
    if prop:
        lines.append(prop)
    after = gifts.get("residue") or "the people I name when I sign"
    home = gifts.get("home")
    return [
        {"heading": "The trust", "paragraphs": lines, "notes": ["Revocable means you can change it or end it while you have capacity."]},
        {"heading": "After my death", "paragraphs": [f"The trustee gives what is then in the trust to {after}."], "notes": ["Only assets that were transferred in are in the trust."]},
        {"heading": "What still has to be transferred", "paragraphs": [
            "This document does not change a deed or a bank account.",
            ("The home at " + home + " is to be deeded into the trust later." if home else "No home was named. A home stays outside the trust until a deed puts it in."),
            "Do not move a retirement account into the trust, or name the trust as its beneficiary, unless a tax adviser has said so.",
        ], "notes": ["An unfunded trust does not avoid probate."]},
        {"heading": "Pour-over will", "paragraphs": [
            f"I also intend a pour-over will. It gives anything still in my probate estate to the trustee of this trust.",
            "The pour-over will still has to be signed with witnesses, and the assets it covers still go through probate. That is why the transfer into the trust matters.",
        ], "notes": ["The will is the safety net. It is not a substitute for transferring the assets."]},
    ]


def _poa_sections(who, about, people, state) -> list[dict]:
    agent = _name(people.get("primary")) or "the agent I name when I sign"
    when = people.get("when") or "as I choose when I sign"
    powers = people.get("powers") or "the powers I write in before I sign"
    return [
        {"heading": "Agent", "paragraphs": [f"I, {who}, of {state}, name {agent} as my agent for property and money."] + _people_lines(people)[1:], "notes": ["The agent can spend your money. Name someone you trust."]},
        {"heading": "When and what", "paragraphs": [f"The agent may act: {when}.", f"The agent may: {powers}.", "The agent may not make healthcare decisions under this document."], "notes": ["A bank may insist on its own statutory form. Take this draft and ask."]},
        {"heading": "Durability", "paragraphs": ["This power is durable. It continues if I cannot manage my affairs, until I revoke it or I die."], "notes": ["Durable is the opposite of an ordinary power, which would end at incapacity."]},
    ]


def _health_sections(who, about, people, state) -> list[dict]:
    agent = _name(people.get("primary")) or "the agent I name when I sign"
    return [
        {"heading": "Healthcare agent", "paragraphs": [f"I, {who}, of {state}, name {agent} to make healthcare decisions if I cannot make them."] + _people_lines(people)[1:], "notes": ["The agent should not witness the document."]},
        {"heading": "Wishes", "paragraphs": [people.get("wishes") or "I will write my wishes before I sign.", "Organ and tissue donation: " + (people.get("organs") or "not yet chosen") + "."], "notes": ["A hospital may also ask you to complete its own form."]},
        {"heading": "Records", "paragraphs": ["My agent may see the healthcare information needed to make those decisions. This sentence is not a hospital's own HIPAA form. Sign the hospital's form if they ask."], "notes": ["This is permission for the agent, not a medical order."]},
    ]


def _probate(about: dict) -> dict:
    state = _state_of(about) or "the state where they lived"
    name = about.get("decedent") or "the person who died"
    lines = [
        f"{name} died on {about.get('date_of_death') or 'a date not yet entered'}. They lived in {about.get('county', 'the county named')}, {state}.",
        f"The person using this checklist is {about.get('your_name') or 'not yet named'}, who says: {about.get('your_role') or 'role not chosen'}.",
        "Will: " + (about.get("has_will") or "not answered") + ".",
        f"Open the estate, if one is needed, in the probate court for that county in {state}. This website does not file the petition and cannot issue letters.",
        "The time creditors have is fixed by that state. Ask the court. Do not copy a deadline from another state, and do not pay the whole estate out before you know it.",
        "Federal estate tax is separate. It applies only if the estate is over the exemption for the year of death. This checklist does not calculate the tax.",
    ]
    return {
        "title": f"Probate checklist — {name}",
        "notice": f"A checklist for {state}. Not a court filing. Not an England and Wales probate application.",
        "sections": [
            {"heading": "What to do", "paragraphs": lines, "notes": ["Letters from the court are what banks ask for. This page cannot issue them."]},
            {"heading": "Commentary: what this is, and what it is not", "paragraphs": ["This is a United States probate checklist. It does not replace the court's forms."]},
        ],
        "next_steps": _NEXT.get("us_probate", []),
        "sources": list(SOURCES),
    }
