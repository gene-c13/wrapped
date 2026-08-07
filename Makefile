.PHONY: data site clean

# Pull your Spotify data from the Web API into data/api/
data:
	python src/pull_api_data.py

# Export the notebook to a static HTML page for GitHub Pages (docs/index.html).
# --no-input hides code cells so the page shows only headings and charts.
site:
	jupyter nbconvert --to html --no-input \
		--output-dir docs --output index \
		notebooks/playlist_analysis.ipynb

# Remove the exported site.
clean:
	rm -f docs/index.html
