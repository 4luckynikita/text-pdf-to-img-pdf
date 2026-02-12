# text-pdf-to-img-pdf
This repo contains a basic python script to convert regularly formatted text PDFs into image-only, slightly fuzzied up counterparts.
Created as a quick tool to jack up PDFs and test an OCR-optional closed source software for bugs.

## Notes
 - The top of the `rasterize_pdf()` declaration, in the parameters, contains some variables that are pre-set but can be tweaked to the user's liking to worsen PDF quality, if necessary. Feel free to experiment with this to get the result you desire! 

Run by:
 - `pipenv shell` (or venv, your choice)
 - `pip install -r requirements.txt`
 - `python rasterize-pdf.py inputpdfhere.pdf`
