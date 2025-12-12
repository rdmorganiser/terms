document.addEventListener("DOMContentLoaded", () => {
  const filterInput = document.getElementById("filter")
  if (!filterInput) return

  const languageToggle = document.getElementById("language-toggle")
  const languageItems = Array.prototype.slice.call(
    document.querySelectorAll("[data-lang]")
  )

  const availableLanguages = Array.from(
    new Set(
      languageItems
        .map((item) => item.getAttribute("data-lang"))
        .filter((lang) => lang)
    )
  ).sort()

  const addLanguageOptions = () => {
    if (!languageToggle || availableLanguages.length === 0) return

    const current = languageToggle.value
    availableLanguages.forEach((lang) => {
      if (!languageToggle.querySelector(`option[value="${lang}"]`)) {
        const option = document.createElement("option")
        option.value = lang
        option.textContent = lang.toUpperCase()
        languageToggle.appendChild(option)
      }
    })

    const preferred = localStorage.getItem("rdmo-terms-language") || (availableLanguages.includes("en") ? "en" : current)
    if (preferred && languageToggle.querySelector(`option[value="${preferred}"]`)) {
      languageToggle.value = preferred
    }
  }

  const applyLanguage = (lang) => {
    if (!languageToggle) return

    localStorage.setItem("rdmo-terms-language", lang)

    languageItems.forEach((item) => {
      const itemLang = item.getAttribute("data-lang")
      if (!itemLang) return

      if (lang === "all" || itemLang === lang) {
        item.classList.remove("d-none")
      } else {
        item.classList.add("d-none")
      }
    })
  }

  // Collect all result cards on this page
  const elements = Array.prototype.slice.call(
    document.querySelectorAll(".element[data-uri]")
  )
  if (elements.length === 0) {
    return
  }

  // Map url -> DOM element for quick lookup
  const elementByUri = new Map()
  elements.forEach(element => {
    const url = element.getAttribute("data-uri")
    if (url) {
      elementByUri.set(url, element)
    }
  })

  let miniSearch = null
  let indexReady = false

  // Load index.json from the same directory as this page
  fetch("index.json")
    .then((response) => {
      if (!response.ok) {
        throw new Error("index.json not found for this page")
      }
      return response.json()
    })
    .then((data) => {
      // base fields we always want to index
      const baseFields = ["uri", "uri_path", "comment"]

      // Collect all keys starting with text_ or title_ across ALL items
      const dynamicFieldSet = new Set()

      data.forEach((item) => {
        Object.keys(item).forEach(key => {
          if (/^(text_|title_)/.test(key)) {
            dynamicFieldSet.add(key)
          }
        })
      })

      const dynamicFields = Array.from(dynamicFieldSet)

      // Merge and make sure fields are unique
      const allFields = baseFields.concat(
        dynamicFields.filter((field) => baseFields.indexOf(field) === -1)
      )

      miniSearch = new MiniSearch({
        fields: allFields,
        storeFields: ["uri"],
        idField: "uri"
      })

      const docs = data
        .filter((item) => item.uri && elementByUri.has(item.uri))
        .map((item) => {
          const doc = { uri: item.uri || "" }

          allFields.forEach((field) => {
            // Fall back to empty string if missing / null
            doc[field] = item[field] || ""
          })

          return doc
        })

      miniSearch.addAll(docs)
      indexReady = true
    })
    .catch((err) => console.error("MiniSearch: could not load or build index.json", err))

  const showAll = () => {
    elements.forEach((element) => {
      element.classList.remove("d-none")
    })
  }

  const filterByResults = (results) => {
    const visibleUrls = new Set(results.map((r) => r.id))

    elements.forEach((element) => {
      const url = element.getAttribute("data-uri")
      if (visibleUrls.has(url)) {
        element.classList.remove("d-none")
      } else {
        element.classList.add("d-none")
      }
    })
  }

  const handleInput = (event) => {
    const query = event.target.value.trim()

    if (!indexReady || !miniSearch || !query) {
      showAll()
      return
    }

    let options = {
      prefix: true,
      fuzzy: 0.2
    }

    // if it looks like a URL, search more strictly
    if (/^https?:\/\//.test(query)) {
      options = {
        fields: ["uri", "uri_path", "url"],
        prefix: false,
        fuzzy: false,
        combineWith: "AND"
      }
    }

    const results = miniSearch.search(query, options)

    if (_.isEmpty(results)) {
      elements.forEach((element) => {
        element.classList.add("d-none")
      })
    } else {
      filterByResults(results)
    }
  }

  const debouncedInput = _.debounce(handleInput, 300)

  filterInput.addEventListener("input", debouncedInput)

  addLanguageOptions()
  applyLanguage(languageToggle ? languageToggle.value : "all")

  if (languageToggle) {
    languageToggle.addEventListener("change", (event) => {
      applyLanguage(event.target.value)
    })
  }

})
