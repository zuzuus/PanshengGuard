"""
One email, attacked step by step, with the verdict printed after each change.

Built for explaining the experiment rather than measuring it - the tables in
attack.py answer "how often", this answers "what does it actually look like".
Also makes a good live demo: the audience reads the same sentence the whole way
through while the verdict moves.

Run:  python demo_attack.py
"""

from attack import predict
from evasion import homoglyph, leetspeak
from attack_whitebox import clean_links
from main import THRESHOLD

EMAIL = """URGENT: Your Maybank2u account has been suspended

Dear Customer,

We detected unauthorized access to your account. Your access will be
permanently disabled within 24 hours unless you verify immediately.

Verify here: http://maybank2u-verify-secure.com/login

Maybank Security Team"""


def verdict(text: str) -> str:
    prob = predict(text)
    label = "PHISHING" if prob >= THRESHOLD else "LEGITIMATE"
    bar = "#" * round(prob * 40)
    return f"{label:<11} {prob * 100:5.1f}%  |{bar:<40}|"


def show(step: str, text: str, note: str = "") -> None:
    print(f"\n{'=' * 78}")
    print(f"  {step}")
    if note:
        print(f"  {note}")
    print(f"{'=' * 78}")
    for line in text.strip().splitlines()[:8]:
        print(f"    {line}")
    print()
    print(f"    detector says:  {verdict(text)}")


show("STEP 0 - the original email",
     EMAIL,
     "Nothing changed. This is what a real phishing email looks like.")

# --- attack 1: swap letters for identical-looking ones -------------------
step1 = homoglyph(EMAIL)
show("STEP 1 - swap letters for lookalikes from another alphabet",
     step1,
     "Read it. It looks identical. Some letters are now Cyrillic, not Latin.")

# --- attack 2: also scramble with digits ---------------------------------
step2 = leetspeak(step1)
show("STEP 2 - also replace letters with digits and symbols",
     step2,
     "Now it is visible, but you can still read it without effort.")

# --- attack 3: clean the link --------------------------------------------
step3 = clean_links(step2)
show("STEP 3 - and host the page on a domain that looks legitimate",
     step3,
     "The wording is mangled AND the link no longer looks wrong.")

print(f"\n{'=' * 78}")
print("  WHAT JUST HAPPENED")
print(f"{'=' * 78}")
print("""
    A human reads all four versions as the same threatening email.

    The detector does not. Each change removes one of the things it was
    relying on:

      the letters    -> the words no longer match anything it learned
      the digits     -> what is left is mangled further
      the link       -> the structural check stops firing

    Only the last two together move the verdict. That is the finding:
    neither attack works alone, but combined they halve detection across
    the whole dataset.
""")
