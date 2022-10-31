import json
import math
import os
from uuid import uuid1

from monzo.authentication import Authentication
from monzo.endpoints.account import Account
from monzo.endpoints.pot import Pot
from monzo.exceptions import MonzoAuthenticationError, MonzoServerError
from rounder.utils import read_from_file, save_to_file


class BalanceManager:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "https://funky-monkey.markmcw.uk",
        oauth_file: str = "/app/config/oauth.json",
    ):
        self.access_token = None
        self.expiry = None
        self.refresh_token = None
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.client = None
        self.oauth_file = oauth_file

        self.build_client()
        self.accounts = self.get_accounts()
        self.main_account_id, self.main_account_balance = self.find_accounts()
        self.round_savings_account_id = self.find_pot()

    def get_oauth_creds(self):
        try:
            content = read_from_file(self.oauth_file)
            content = json.loads(content)
            self.access_token = content["access_token"]
            self.expiry = content["expiry"]
            self.refresh_token = content["refresh_token"]
        except FileNotFoundError:
            return
        except Exception as e:
            print(f"Exception loading content from file: {e}")

    def write_oauth_creds(self):
        credentials = {
            "refresh_token": self.client.refresh_token,
            "expiry": self.client.access_token_expiry,
            "access_token": self.client.access_token,
        }
        save_to_file(credentials, self.oauth_file)

    def build_client(self):
        self.get_oauth_creds()
        self.client = Authentication(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_url=self.redirect_uri,
            access_token=self.access_token,
            access_token_expiry=self.expiry,
            refresh_token=self.refresh_token,
        )
        if self.client.refresh_token:
            self.write_oauth_creds()
        else:
            print("OAuth Activation Required. Please follow the link below and paste the outputs from the URL.")
            print(self.client.authentication_url)
            self.get_state_from_user()

    def get_state_from_user(self):
        try:
            auth_token = input("Auth Token:")
            state_token = input("State Token:")
            self.client.authenticate(auth_token, state_token)

            self.write_oauth_creds()
        except MonzoAuthenticationError:
            print("State code does not match")
            exit(1)
        except MonzoServerError:
            print("Monzo Server Error")
            exit(1)

    def get_accounts(self):
        return Account.fetch(self.client)

    def get_pots(self):
        return Pot.fetch(self.client, self.main_account_id)

    def find_accounts(self) -> tuple[str, int]:
        for account in self.accounts:
            if account.account_type() == "Current Account" and account.balance.total_balance != 0:
                return account.account_id, account.balance.balance
        raise KeyError("Cannot find Current Account")

    def find_pot(self):
        active_pots = [pot for pot in self.get_pots() if not pot.deleted]
        for pot in active_pots:
            if pot.name == "Rounder":
                return pot.pot_id
        raise KeyError('Cannot find pot with name "Rounder"')

    def determine_rounding(self):
        balance = self.main_account_balance
        new_balance = math.floor(balance / 500) * 500
        diff = balance - new_balance
        if diff != 0:
            print(f"💰 Going to move {diff} to {self.round_savings_account_id}")
            self.make_transfer(diff)
        else:
            print("No rounding required. Cya later alligator 🐊")

    def make_transfer(self, amount: int):
        pot = Pot.fetch_single(self.client, self.main_account_id, self.round_savings_account_id)
        Pot.deposit(self.client, pot, self.main_account_id, amount, str(uuid1()))


if __name__ == "__main__":
    x = BalanceManager(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
    )
    x.determine_rounding()
