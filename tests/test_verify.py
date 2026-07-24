from decimal import Decimal

from tracker.verify import verify_price

# WooCommerce-style sale: regular price struck through in <del>, sale in <ins>.
_SALE_HTML = """
<div class="summary"><p class="price">
  <del><span class="woocommerce-Price-amount">1199.00&nbsp;&euro;</span></del>
  <ins><span class="woocommerce-Price-amount">849.00&nbsp;&euro;</span></ins>
</p></div>
<div class="related"><p class="price">
  <del><span class="woocommerce-Price-amount">20.50&nbsp;&euro;</span></del>
  <ins><span class="woocommerce-Price-amount">14.00&nbsp;&euro;</span></ins>
</p></div>
"""

_PLAIN_HTML = '<div class="summary"><p class="price">849.00&nbsp;&euro;</p></div>'


def test_flags_regular_price_when_sale_shown():
    # Scraped the regular price (1199) while the page sells it for 849.
    res = verify_price(_SALE_HTML, Decimal("1199.00"))
    assert res.ok is False
    assert "849" in res.note and "1,199" in res.note


def test_silent_when_scraped_price_is_the_sale_price():
    # Scraped the actual sale price — no warning.
    assert verify_price(_SALE_HTML, Decimal("849.00")).ok is True


def test_does_not_cross_with_accessory_sale():
    # A scraped price matching no <del> must not borrow the accessory's sale price.
    assert verify_price(_SALE_HTML, Decimal("950.00")).ok is True


def test_silent_without_sale_markup():
    assert verify_price(_PLAIN_HTML, Decimal("1199.00")).ok is True


def test_silent_on_empty_inputs():
    assert verify_price(None, Decimal("10")).ok is True
    assert verify_price("<html></html>", None).ok is True
