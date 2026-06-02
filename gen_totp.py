import pyotp
import sys

secret = "ASP6BKFCBRHSIQL74XYIWKT6ICVHFXTW"
totp = pyotp.TOTP(secret)
print(totp.now())
