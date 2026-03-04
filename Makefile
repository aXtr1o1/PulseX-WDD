# WDD PulseX Seeding & Runtime Management

.PHONY: seed reset-runtime help

help:
	@echo "Usage:"
	@echo "  make seed           - Generate PalmX-grade seed data"
	@echo "  make reset-runtime  - Clear runtime data and re-seed"

seed:
	@echo "Refining seed data..."
	python3 scripts/seed_leads.py

reset-runtime:
	@echo "Resetting runtime files..."
	rm -rf runtime/leads/*.csv
	rm -rf runtime/sessions.csv
	$(MAKE) seed
