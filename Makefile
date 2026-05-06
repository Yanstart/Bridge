# =====================================================================
# Makefile - Projet IoT Edge Bridge - EPHEC TS6 2025-2026
# Auteur : Noel Junior Yando Fotso
#
# Sources LaTeX : src/
# PDFs livrables : pdf/
# Compilation : XeLaTeX + biber via latexmk
# Les PDFs compiles sont copies dans pdf/ apres chaque compilation reussie.
# =====================================================================

LATEXMK     = latexmk
LATEX_FLAGS = -xelatex -shell-escape -interaction=nonstopmode -halt-on-error -file-line-error -cd
SRC_DIR     = src
PDF_DIR     = pdf
TARGETS     = rapport pitch cdc

.PHONY: all rapport pitch pitch-notes cdc clean distclean help

all: $(TARGETS)

rapport:
	$(LATEXMK) $(LATEX_FLAGS) $(SRC_DIR)/rapport.tex
	@mkdir -p $(PDF_DIR)
	@cp $(SRC_DIR)/rapport.pdf $(PDF_DIR)/rapport.pdf

pitch:
	$(LATEXMK) $(LATEX_FLAGS) $(SRC_DIR)/pitch.tex
	@mkdir -p $(PDF_DIR)
	@cp $(SRC_DIR)/pitch.pdf $(PDF_DIR)/pitch.pdf

# Pitch en mode "notes a droite" pour pdfpc/Skim/Acrobat dual-ecran.
# Le wrapper src/pitch-notes.tex active le toggle puis charge pitch.tex.
# Resultat : pdf/pitch-notes.pdf, chaque page deux fois plus large
# (slide a gauche, notes orateur a droite).
pitch-notes:
	$(LATEXMK) $(LATEX_FLAGS) $(SRC_DIR)/pitch-notes.tex
	@mkdir -p $(PDF_DIR)
	@cp $(SRC_DIR)/pitch-notes.pdf $(PDF_DIR)/pitch-notes.pdf
	@echo ""
	@echo "PDF avec notes pret : $(PDF_DIR)/pitch-notes.pdf"
	@echo "Utilise avec : pdfpc $(PDF_DIR)/pitch.pdf  (lit les notes Beamer natives)"
	@echo "Ou ouvre ce PDF sur ton portable, projette pitch.pdf sur le second ecran."

cdc:
	$(LATEXMK) $(LATEX_FLAGS) $(SRC_DIR)/cdc.tex
	@mkdir -p $(PDF_DIR)
	@cp $(SRC_DIR)/cdc.pdf $(PDF_DIR)/cdc.pdf

# Nettoyage des fichiers auxiliaires dans src/
clean:
	$(LATEXMK) -c -cd $(SRC_DIR)/rapport.tex
	$(LATEXMK) -c -cd $(SRC_DIR)/pitch.tex
	$(LATEXMK) -c -cd $(SRC_DIR)/cdc.tex
	-rm -f $(SRC_DIR)/*.aux $(SRC_DIR)/*.bbl $(SRC_DIR)/*.bcf $(SRC_DIR)/*.bcf-SAVE-ERROR
	-rm -f $(SRC_DIR)/*.bbl-SAVE-ERROR $(SRC_DIR)/*.blg
	-rm -f $(SRC_DIR)/*.fdb_latexmk $(SRC_DIR)/*.fls $(SRC_DIR)/*.log
	-rm -f $(SRC_DIR)/*.lof $(SRC_DIR)/*.lot $(SRC_DIR)/*.nav
	-rm -f $(SRC_DIR)/*.out $(SRC_DIR)/*.run.xml $(SRC_DIR)/*.snm
	-rm -f $(SRC_DIR)/*.toc $(SRC_DIR)/*.synctex.gz $(SRC_DIR)/*.glo
	-rm -f $(SRC_DIR)/*.glsdefs $(SRC_DIR)/*.acn $(SRC_DIR)/*.acr
	-rm -f $(SRC_DIR)/*.alg $(SRC_DIR)/*.ist $(SRC_DIR)/*.gls
	-rm -f $(SRC_DIR)/*.glg $(SRC_DIR)/*.xdy $(SRC_DIR)/*.xdv $(SRC_DIR)/*.vrb
	-rm -f $(SRC_DIR)/rapport/*.aux $(SRC_DIR)/cdc/*.aux

# Nettoyage complet : supprime aussi les .pdf intermediaires dans src/
# (les PDFs deja copies dans pdf/ sont preserves)
distclean: clean
	-rm -f $(SRC_DIR)/rapport.pdf $(SRC_DIR)/pitch.pdf $(SRC_DIR)/cdc.pdf
	-rm -f $(SRC_DIR)/pitch-notes.pdf $(SRC_DIR)/pitch-notes.aux $(SRC_DIR)/pitch-notes.log
	-rm -f $(SRC_DIR)/pitch-notes.fdb_latexmk $(SRC_DIR)/pitch-notes.fls
	-rm -f $(SRC_DIR)/pitch-notes.nav $(SRC_DIR)/pitch-notes.out
	-rm -f $(SRC_DIR)/pitch-notes.snm $(SRC_DIR)/pitch-notes.toc
	-rm -f $(SRC_DIR)/pitch-notes.vrb $(SRC_DIR)/pitch-notes.xdv

help:
	@echo "Cibles disponibles :"
	@echo "  make all          Compile rapport, pitch et cdc, copie les PDFs dans pdf/"
	@echo "  make rapport      Compile src/rapport.tex"
	@echo "  make pitch        Compile src/pitch.tex (PDF de projection, slides seules)"
	@echo "  make pitch-notes  Compile pitch en mode dual-ecran (slides + notes orateur a droite)"
	@echo "  make cdc          Compile src/cdc.tex"
	@echo "  make clean        Supprime les fichiers temporaires LaTeX dans src/"
	@echo "  make distclean    Supprime aussi les .pdf intermediaires dans src/"
