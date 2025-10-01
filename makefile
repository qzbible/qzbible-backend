config:
	docker compose -f local.yml config 
build:
	docker compose -f local.yml up --build -d --remove-orphans
up_lo:
	docker compose -f local.yml up -d

down_lo:
	docker compose -f local.yml down

show_logs_lo:
	docker compose -f local.yml logs