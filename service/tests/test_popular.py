import asyncio

from fakes import FakeNet, internet

from bawabu_service import popular
from bawabu_service.popular import Popular

NAMES = Popular(["react", "express", "react-dom", "@types/node", "lodash", "vue", "requests"])


def test_one_typo_away_is_a_lookalike():
    assert NAMES.lookalike("raect") == "react"          # swapped letters
    assert NAMES.lookalike("expres") == "express"       # missing letter
    assert NAMES.lookalike("lodashh") == "lodash"       # extra letter
    assert NAMES.lookalike("reqests") == "requests"
    assert NAMES.lookalike("@types/nodee") == "@types/node"


def test_separator_variants_are_lookalikes():
    assert NAMES.lookalike("react_dom") == "react-dom"
    assert NAMES.lookalike("reactdom") == "react-dom"
    assert NAMES.lookalike("types-node") == "@types/node"


def test_popular_names_and_unrelated_names_are_not_lookalikes():
    assert NAMES.lookalike("react") is None
    assert NAMES.lookalike("React") is None
    assert NAMES.lookalike("zod") is None
    assert NAMES.lookalike("vux") is None  # too short to call a typo


def test_the_vendored_npm_list():
    names = popular.npm()
    assert "react" in names and "@types/node" in names
    assert names.lookalike("reacct") == "react"


def test_suggestions_prefer_a_typo_match_then_npm_search():
    net = internet()
    client = net.client()
    assert asyncio.run(popular.suggest(client, "npm", "expresss", popular.npm())) == "express"
    # Not a typo of anything popular: npm search, most downloads among close names.
    assert asyncio.run(popular.suggest(client, "npm", "fancy-date-pickr", popular.npm())) == "react-datepicker"
    assert asyncio.run(popular.suggest(client, "npm", "zzz-nothing-like-it", popular.npm())) is None


def test_pypi_list_is_fetched_once_and_failures_are_survivable():
    popular._pypi = None
    net = FakeNet()
    client = net.client()
    names = asyncio.run(popular.for_ecosystem(client, "pypi"))
    assert names.lookalike("reqeusts") == "requests"
    asyncio.run(popular.for_ecosystem(client, "pypi"))
    assert net.hits("hugovk.github.io") == 1
    popular._pypi = None
    net.down.add("hugovk.github.io")
    assert asyncio.run(popular.for_ecosystem(client, "pypi")) is None
    popular._pypi = None


def test_misspelled_words_are_fixed_and_the_closest_popular_name_is_suggested():
    names = popular.npm()
    assert names.correct("react-datepickr") == "react-datepicker"
    assert names.correct("prisma-clinet") == "prisma-client"
    client = FakeNet().client()
    cases = {
        "react-datepickr": "react-datepicker",
        "expresss-validator": "express-validator",
        "axois": "axios",
        "mongose": "mongoose",
        "prisma-clinet": "@prisma/client",
        "tailwind-css-animate": "tailwindcss-animate",
    }
    for made_up, real in cases.items():
        assert asyncio.run(popular.suggest(client, "npm", made_up, names)) == real, made_up
