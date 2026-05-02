# Master ʻŌlelo Hawaiʻi Vocabulary

A focused way to learn Hawaiian by mastering the 2,000 most useful words.

**Live at [olelodaily.com](https://olelodaily.com)**

## Why 2,000 words

Decades of language research show the same pattern across every language studied. The 2,000 most used words cover roughly 95 percent of everyday speech and writing. Hit that milestone and you stop reaching for a dictionary every other sentence. You start understanding.

Hawaiian works the same way. The same core nouns, verbs, and connectors do the heavy lifting in conversation, mele, moʻolelo, and the news. Lock in those 2,000 and you have a real working command of the language.

This app tracks your path to all 2,000. Every word you master moves the needle.

## What it does

Short daily rounds. Each round shows you a word in Hawaiian, you translate it to English, then it shows you the same word in English and you translate it back. Two way recall is what builds real fluency.

Words you miss come back fast. Words you nail check in less often. The spacing schedule is set so your brain locks the words in for the long haul rather than cramming and forgetting.

Typos with the kahakō or ʻokina still count. Close spelling still counts. The point is knowing the word, not punishing the keyboard.

## What's in the data

Over 2,600 vocabulary entries across nouns, verbs, phrases, numbers, pronouns, time words, idioms, and ʻōlelo noʻeau. Every entry uses correct ʻokina and kahakō.

Breakdown by type lives in `data.js`. Each entry has a stable ID so progress tracking survives data updates.

## How it works

Static HTML, vanilla JavaScript, no build step. The whole app is two files.

- `index.html` is the app
- `data.js` is the vocabulary

Progress saves to cookies on the device. No accounts. No tracking. No analytics. Nothing leaves the browser.

The spacing engine is a six level mastery ladder. Each correct round bumps a word up a level. Each missed round drops it back. Words at higher levels reappear less often. After level 5 a word is considered mastered and only checks in periodically to keep it fresh.

## Running it locally

Clone the repo and open `index.html` in a browser. That's it.

```
git clone https://github.com/olagon/learnhawaiian.git
cd learnhawaiian
open index.html
```

Or serve it with any static file server if you want a real URL during development.

```
python3 -m http.server 8000
```

Then visit http://localhost:8000

## Roadmap

- Optional account login for cross device progress sync
- Audio for each word with native pronunciation
- Sentence level practice once core vocabulary is solid
- ʻŌlelo noʻeau deep dive mode
- Export progress as CSV for personal review

## Contributing

Vocabulary corrections are especially welcome. If you spot a wrong translation, a missing kahakō, or an ʻokina in the wrong place, open an issue or a pull request with the entry ID and the correction.

For new words, the bar is high. Every entry has to be 100 percent accurate with proper diacritics. Cite a source (Pukui-Elbert dictionary, Hawaiian Dictionary online at wehewehe.org, or another reputable reference) when proposing additions.

## License

Open source under the [MIT License](https://opensource.org/licenses/MIT).

The vocabulary data is also released under MIT for free use in any project.

## Credit

Built with aloha by [Olin Kealoha Lagon](https://www.linkedin.com/in/olinlagon/).

He aliʻi ka ʻāina, he kauwā ke kanaka. The land is chief, the people are its servants.
