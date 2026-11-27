# Zero-burn desk health targets. All modes are paper-only / read-only by default.
.PHONY: run-nice check tests simulator

run-nice: check tests simulator
	@echo "═══ LYTA desk health: ALL STEPS OK ═══"

check:
	cd lyta-grok-desk && bun run check

tests:
	python3 -m pytest test_paper_desk_simulator.py -q

simulator:
	python3 pumpfun_desk_simulator.py --quiet
