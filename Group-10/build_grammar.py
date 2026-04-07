from tree_sitter import Language

# Build a shared library with only Python grammar
Language.build_library(
    'build/my-languages.so',  # output file
    [
        'tree-sitter-python'  # path to downloaded Python grammar
    ]
)
