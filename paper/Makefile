# Makefile for LaTeX Paper Compilation with XeLaTeX

MAIN = main
BIB = references

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex $(BIB).bib
	xelatex $(MAIN)
	bibtex $(MAIN)
	xelatex $(MAIN)
	xelatex $(MAIN)

clean:
	rm -f *.aux *.log *.out *.toc *.bbl *.blg *.pdf
	rm -rf sections/ scripts/ figures/

