import pyotp
import qrcode
import io
import base64


class TOTPService:
    @staticmethod
    def generate_secret() -> str:
        """Generate a random base32 secret."""
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(
        email: str, secret: str, issuer_name: str = "JobMatch AI"
    ) -> str:
        """Generate the provisioning URI for QR codes."""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=email, issuer_name=issuer_name
        )

    @staticmethod
    def verify_code(secret: str, code: str, valid_window: int = 1) -> bool:
        """Verify a 6-digit TOTP code.

        Args:
            secret: The TOTP secret
            code: The 6-digit code to verify
            valid_window: Number of timesteps (30s each) to allow for time drift (default: 1)
        """
        if not secret or not code:
            return False
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=valid_window)

    @staticmethod
    def generate_qr_base64(uri: str) -> str:
        """Generate a base64 encoded QR code image."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()


totp_service = TOTPService()
