all: node_modules
	npm run htmlhint
	npm run stylelint

node_modules:
	npm install
