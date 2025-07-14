import appgrowth, sys

if not appgrowth.login():
    sys.exit("Login failed")

ok = appgrowth.create_segment(
    name="bloom_com.easybrain.number.puzzle.game_THA_95_TEST",
    title="com.easybrain.number.puzzle.game",
    app="com.easybrain.number.puzzle.game",
    country="THA",
    audience=0.95,
)
print("Segment created?", ok)


