#!/usr/bin/env python3
"""Narrated step videos when the talking-head tools are not on this machine.

Uses a British English voice and the existing presenter still, with the same
captions file the player already expects. Re-running skips a clip that is
already a real file (20 KB or larger) unless --force is set.

  python video/render_narration.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "videos"
SCRIPTS = ROOT / "video" / "scripts.json"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
VOICE = "en-GB-SoniaNeural"
STILL = OUT / "will_intro.jpg"
SUFFIX = ""
MIN_BYTES = 20_000

EXTRA = {
    "will_business": {"title": "Your business", "lines": [
        "If you own a business, a farm, agricultural land, or shares in a company, tell us here.",
        "A solicitor looks at how those assets should pass, and whether they should stay separate from the rest of your estate.",
        "Some business and farm assets can qualify for inheritance tax business relief, but the rules are detailed and they change. Do not rely on a summary. A solicitor must check.",
        "If there are co-owners, talk to them first, and check any partnership or shareholders' agreement.",
        "This will is not a lasting power of attorney. If you want someone to run the business while you are alive but cannot decide, that is a separate LPA."]},
    "lpa_signing": {"title": "The order of signing", "lines": [
        "The Office of the Public Guardian will not register a lasting power of attorney unless everyone signs the same original paper form, in the right order.",
        "You, the donor, sign first. On a health and welfare LPA, sign section five, about life-sustaining treatment, before section nine. If you used a continuation sheet, sign that before section nine as well. Then sign section nine.",
        "A witness aged eighteen or over must watch you sign, and sign straight after you. An attorney or a replacement attorney cannot be that witness. Your certificate provider can.",
        "The certificate provider signs section ten next. They must sign after you, and before any attorney.",
        "Each attorney and each replacement attorney then signs section eleven. Someone must witness them. You cannot be that witness. Attorneys can witness each other, but nobody witnesses their own signature.",
        "The person applying to register signs section fifteen last, and dates it after every attorney has signed. If the order is wrong, the LPA cannot be registered, and the attorneys cannot use it.",
    ]},
    "lpa_property_business": {"title": "Business or personal finances", "lines": [
        "If you have a business, a farm, or company shares, you can keep them apart from your personal finances.",
        "To use different attorneys for the business and for your household, make two property and financial lasting powers of attorney, not one.",
        "Official guidance says an instruction that splits the work between attorneys on a single form can stop the LPA working.",
        "Talk to any co-owners first, and check the partnership agreement, shareholders' agreement, or articles. A solicitor should check both forms before you sign."]},
    "poa_intro": {"title": "Ordinary power of attorney", "lines": [
        "This is an ordinary power of attorney for England and Wales. It is sometimes called a general power.",
        "It lets someone act for you while you still have mental capacity. You sign it as a deed in front of a witness. You do not register it with the Office of the Public Guardian.",
        "It stops if you die, become bankrupt, or lose mental capacity. It is not a lasting power of attorney. If you want someone to act after you lose capacity, you need an LPA as well.",
        "Use a general power for broad authority, for example while you are abroad. Use a specific power when you want one exact task, such as one property sale."]},
    "poa_type": {"title": "General or specific", "lines": [
        "A general power uses the short form in Schedule one to the Powers of Attorney Act nineteen seventy-one. It is wide.",
        "A specific power is limited to one task. It is not a statutory form, and a solicitor should check it, especially if it deals with land.",
        "Please confirm you understand that this power stops if you lose mental capacity."]},
    "poa_donor": {"title": "About you", "lines": [
        "You are the donor. Please use your full legal name and the address you want on the deed.",
        "You must have mental capacity when you sign. You sign in front of an independent adult witness, who then signs and adds their name, address and occupation."]},
    "poa_attorneys": {"title": "Your attorneys", "lines": [
        "Choose one attorney, or more than one, that you trust.",
        "If you appoint more than one, say whether they must all agree, or whether they can act together or on their own."]},
    "poa_authority": {"title": "What the power covers", "lines": [
        "A general power does not list every task. The Act sets how wide it is. It does not usually cover things you do as a trustee or as a personal representative.",
        "For a specific power, describe the one task in plain language. Do not try to turn it into a general power.",
        "If you want it to end on a date, or when the task is finished, a solicitor must check that extra wording before you sign."]},
    "poa_review": {"title": "Check and sign", "lines": [
        "Please read the draft. Nothing is signed from this website.",
        "A solicitor reviews it first. Then you sign the deed in front of a witness.",
        "It can be used at once. It is not registered with the Office of the Public Guardian, and it ends if you lose mental capacity."]},
    "prenup_intro": {"title": "Prenuptial agreement", "lines": [
        "A prenuptial agreement is signed before you marry or form a civil partnership.",
        "In England and Wales it is not automatically binding. A court is more likely to follow it if it is fair, both of you had your own legal advice, and you each disclosed your finances.",
        "These questions collect what you want. Do not sign anything until both of you have spoken to your own solicitors."]},
    "prenup_parties": {"title": "About both of you", "lines": [
        "Please use both full legal names, and the date you expect to marry or form a civil partnership.",
        "The agreement is between the two people who intend to marry."]},
    "prenup_assets": {"title": "Assets and disclosure", "lines": [
        "Full disclosure matters. List the main assets each of you is bringing in: property, savings, pensions, and any business.",
        "Say what you both want the agreement to achieve, and any assets you want to keep completely separate.",
        "Approximate values are enough for now. Your solicitor will refine the list."]},
    "prenup_arrangements": {"title": "How assets should be treated", "lines": [
        "Describe what should happen to the family home, and any income or maintenance you want to set out, if the marriage ends.",
        "These are your instructions. A solicitor writes the formal clauses."]},
    "prenup_review": {"title": "Review and next steps", "lines": [
        "A solicitor reviews these answers and prepares the formal agreement.",
        "Each of you needs your own legal advice, and you exchange full financial disclosure, before anyone signs."]},
    "postnup_intro": {"title": "Postnuptial agreement", "lines": [
        "A postnuptial agreement is signed after you are already married or in a civil partnership.",
        "It is not automatically binding. A court can take it into account if it is fair and both of you had independent legal advice."]},
    "postnup_parties": {"title": "The parties", "lines": [
        "Please enter both full legal names, and the date of the marriage or civil partnership."]},
    "postnup_assets": {"title": "Assets and intentions", "lines": [
        "Describe the main assets the agreement should cover, and what you both want it to achieve.",
        "Your solicitor will turn this into the formal terms and arrange full disclosure."]},
    "postnup_review": {"title": "Review", "lines": [
        "A solicitor reviews the draft before anyone signs. Both of you should take your own legal advice."]},
    "cohab_intro": {"title": "Cohabitation agreement", "lines": [
        "If you live together and you are not married or in a civil partnership, you do not have the same automatic rights.",
        "A cohabitation agreement can say who owns the home and the money, and what happens if you separate.",
        "A solicitor checks the draft before you sign."]},
    "cohab_parties": {"title": "The parties", "lines": [
        "Please enter both full names, and the address where you live together."]},
    "cohab_property": {"title": "Property and money", "lines": [
        "Describe the home, who paid what, and how you own it.",
        "Then say what should happen to the property and the money if you separate."]},
    "cohab_review": {"title": "Review", "lines": [
        "A solicitor reviews this before you sign. Living together does not, by itself, give you a share of your partner's property."]},
    "employment_intro": {"title": "Settlement agreement", "lines": [
        "A settlement agreement is a way to end employment on agreed terms.",
        "It usually means the employee gives up certain claims. For that to work, the employee must receive independent legal advice before signing.",
        "Do not sign until that advice has been given."]},
    "employment_parties": {"title": "Parties and employment", "lines": [
        "Please enter the employer's name, the employee's full name, the job title, and the proposed date the employment would end."]},
    "employment_terms": {"title": "Settlement terms", "lines": [
        "Set out the payment, when it is paid, and any notice.",
        "You can also note a reference, confidentiality, or other terms. A solicitor writes the formal clauses."]},
    "employment_review": {"title": "Review", "lines": [
        "A solicitor reviews the draft. The employee must take independent advice on the agreement before it can settle claims."]},
}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write((r.stderr or r.stdout)[-2000:])
        raise SystemExit(f"failed: {cmd[0]}")
    return r.stderr


def duration(path: Path) -> float:
    err = subprocess.run(["ffmpeg", "-i", str(path)], capture_output=True, text=True).stderr
    for line in err.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise SystemExit(f"no duration for {path}")


def vtt_time(t: float) -> str:
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


async def speak(line: str, dest: Path):
    import edge_tts
    await edge_tts.Communicate(line, VOICE, rate="-4%").save(str(dest))


def render_one(vid: str, spec: dict, work: Path):
    lines = spec["lines"]
    title = spec["title"]
    clip = work / vid
    if clip.exists():
        shutil.rmtree(clip)
    clip.mkdir(parents=True)
    durations = []
    for i, line in enumerate(lines):
        dest = clip / f"line_{i:02d}.mp3"
        asyncio.run(speak(line, dest))
        durations.append(duration(dest))
    silence = clip / "gap.wav"
    lead = clip / "lead.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.35", str(silence)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.4", str(lead)])
    wavs = [lead]
    cues, t = [], 0.4
    for i, (line, d) in enumerate(zip(lines, durations)):
        wav = clip / f"line_{i:02d}.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip / f"line_{i:02d}.mp3"), "-ar", "24000", "-ac", "1", str(wav)])
        wavs += [wav, silence]
        cues.append((t, t + d, line))
        t += d + 0.35
    concat = clip / "concat.txt"
    concat.write_text("".join(f"file '{p}'\n" for p in wavs))
    audio = clip / "narration.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(audio)])
    from PIL import Image, ImageDraw, ImageFont
    title_img = clip / "title.png"
    bar = Image.new("RGBA", (720, 64), (20, 33, 61, 214))
    draw = ImageDraw.Draw(bar)
    draw.text((22, 16), title, font=ImageFont.truetype(FONT, 28), fill="white")
    bar.save(title_img)
    brand = clip / "brand.png"
    mark = Image.new("RGBA", (280, 36), (0, 0, 0, 0))
    ImageDraw.Draw(mark).text((0, 4), "Signed and Sorted", font=ImageFont.truetype(FONT_REG, 20), fill=(255, 255, 255, 230))
    mark.save(brand)
    mp4 = OUT / f"{vid}{SUFFIX}.mp4"
    vf = (
        "[0:v]scale=1400:788,"
        "zoompan=z='min(1+0.00028*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=960x540:fps=25[bg];"
        "[bg][2:v]overlay=20:H-110:enable='between(t,0.3,6.5)'[t];"
        "[t][3:v]overlay=W-w-22:18[out]"
    )
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25", "-i", str(STILL), "-i", str(audio),
         "-i", str(title_img), "-i", str(brand), "-filter_complex", vf, "-map", "[out]", "-map", "1:a:0",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
         "-shortest", "-movflags", "+faststart", str(mp4)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.2", "-i", str(mp4), "-frames:v", "1", "-q:v", "4", str(OUT / f"{vid}{SUFFIX}.jpg")])
    (OUT / f"{vid}{SUFFIX}.vtt").write_text("WEBVTT\n\n" + "\n".join(
        f"{i}\n{vtt_time(a)} --> {vtt_time(b)}\n{text}\n" for i, (a, b, text) in enumerate(cues, 1)))
    print(f"[done] {vid} {mp4.stat().st_size // 1024} KB", flush=True)


def main():
    global SUFFIX, VOICE, STILL
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--suffix", default="")
    ap.add_argument("--voice", default="en-GB-SoniaNeural")
    ap.add_argument("--still", default="")
    args = ap.parse_args()
    SUFFIX = args.suffix
    VOICE = args.voice
    STILL = Path(args.still) if args.still else OUT / "will_intro.jpg"
    scripts = json.loads(SCRIPTS.read_text())
    for key, spec in EXTRA.items():
        scripts.setdefault(key, spec)
    SCRIPTS.write_text(json.dumps(scripts, indent=1, ensure_ascii=False) + "\n")
    only = {x for x in args.only.split(",") if x}
    work = Path("/tmp/narration-work")
    work.mkdir(exist_ok=True)
    for vid, spec in scripts.items():
        if vid.startswith("_") or not isinstance(spec, dict) or "lines" not in spec:
            continue
        if only and vid not in only:
            continue
        mp4 = OUT / f"{vid}{SUFFIX}.mp4"
        if mp4.exists() and mp4.stat().st_size >= MIN_BYTES and not args.force:
            continue
        render_one(vid, spec, work)


if __name__ == "__main__":
    main()
