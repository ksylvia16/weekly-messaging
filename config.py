from datetime import datetime

# 📂 Map CSV filenames → instructors
# Keys must include the .csv extension exactly as on disk
CSV_TO_INSTRUCTOR = {
    "WD Section 1A.csv": "@Barent",
    "DC Section 1A.csv": "@Katie",
    "DA Section 1A.csv": "@Sarah Cole",
    "DM Section 1A.csv": "@Lynette Williams",
    "RT Section 1A.csv": "@Jen Crompton",
    "WD Section 1B.csv": "@Jazz Inneh",
    "DC Section 1B.csv": "@Mark Vigeant",
    "DA Section 1B.csv": "@Katie",
    "DM Section 1B.csv": "@Phillip Robinson",
    "RT Section 1B.csv": "@Lynette Williams",
    "WD Section 2A.csv": "@Kat (she/her)",
    "DC Section 2A.csv": "@Steven Johnson",
    "DA Section 2A.csv": "@Tara Tran",
    "DM Section 2A.csv": "@Phillip Robinson",
    "RT Section 2A.csv": "@Ianne (she/her)",
    "WD Section 2B.csv": "@Barent",
    "DC Section 2B.csv": "@Pete (he/him)",
    "DA Section 2B.csv": "@Tara Tran",
    "DM Section 2B.csv": "@Jennifer R",
    "RT Section 2B.csv": "@Phillip Robinson",
    "WD Section 2C.csv": "@Jazz Inneh",
    "DC Section 2C.csv": "@Pete (he/him)",
    "DA Section 2C.csv": "@Austin Roach",
    "DM Section 2C.csv": "@Jennifer R",
    "RT Section 2C.csv": "@Lynette Williams",
    "RT Section 3A.csv": "@Katie"

}

# 🏷️ Optional term label shown in the header (set to None to show date range instead)
TERM_LABEL = None  # e.g., "Week 4 of Fall '25"

# 🧩 Header template (use {header_label})
HEADER_TEMPLATE = "Happy {header_label}! :fallen_leaf:"

# 🔹 How many placeholder bullets to show under each lab line
LAB_PLACEHOLDER_BULLETS = 1

# 🗂️ Optional: normalize lab titles (useful if CSV titles vary but you want a single display title)
LAB_TITLE_NORMALIZATION = {
    # "what is a data analyst?!": "What is a Data Analyst?!",
    # "a/b testing w/ buzzfeed": "A/B Testing w/ BuzzFeed",
}
