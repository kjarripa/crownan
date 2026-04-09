"""Test CLI commands with mocked KronanClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from crownan.cli import cmd_cart, cmd_me, main
from crownan.models import Checkout, Me


class TestCLICommands:
    def test_cmd_me(self, capsys):
        mock_client = MagicMock()
        mock_client.get_me.return_value = Me(type="user", name="Test User")
        args = MagicMock()
        cmd_me(mock_client, args)
        output = capsys.readouterr().out
        assert "Test User" in output

    def test_cmd_cart_empty(self, capsys):
        mock_client = MagicMock()
        mock_client.get_checkout.return_value = Checkout(
            token="abc",
            total=199,
            subtotal=0,
            bagging_fee=199,
            service_fee=0,
            shipping_fee=0,
            shipping_fee_cutoff=19900,
            lines=[],
        )
        args = MagicMock()
        cmd_cart(mock_client, args)
        output = capsys.readouterr().out
        assert "Cart is empty" in output

    def test_main_no_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("dotenv.load_dotenv"):  # don't load real env
                with patch("sys.argv", ["crownan", "me"]):
                    with pytest.raises(SystemExit):
                        main()
