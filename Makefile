.PHONY: full-check pilot-sbom

full-check:
	./scripts/full-check.sh

pilot-sbom:
	./scripts/generate-pilot-sbom.py --output build/pilot-sbom.cdx.json
