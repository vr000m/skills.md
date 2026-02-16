set dotenv-load := true

sync-skills:
    ./scripts/sync-skills.sh

promote-skills:
    ./scripts/promote-skills.sh --yes

bootstrap-skills:
    ./scripts/bootstrap-skills.sh --yes

check-sync:
    ./scripts/check-sync.sh

lint-scripts:
    shellcheck scripts/*.sh
    shfmt -d scripts/*.sh
