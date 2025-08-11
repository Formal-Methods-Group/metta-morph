#1. We load the file within we want to auto-quote all symbols within the Scheme code from the user's MeTTa code
#   which do not refer to functions, macros, MeTTa variables, types, or boolean/number/string literals:
with open("RUN.scm") as file:
    allcode = file.read()
basecode, usercode = allcode.split(";__METTACODE__:")

# Helper function to remove comments while preserving strings
def remove_comments_preserve_strings(line):
    """Remove comments from a line while preserving content inside string literals."""
    result = []
    in_string = False
    escaped = False
    
    for i, char in enumerate(line):
        if escaped:
            result.append(char)
            escaped = False
            continue
            
        if char == '\\' and in_string:
            result.append(char)
            escaped = True
            continue
            
        if char == '"':
            result.append(char)
            in_string = not in_string
            continue
            
        if char == ';' and not in_string:
            # Found a comment outside of a string
            break
            
        result.append(char)
    
    return ''.join(result)

# Helper function to extract tokens while respecting string boundaries
def extract_tokens_outside_strings(text):
    """Extract tokens from text, excluding content inside string literals."""
    tokens = []
    current_token = []
    in_string = False
    escaped = False
    
    for char in text:
        if escaped:
            escaped = False
            continue
            
        if char == '\\' and in_string:
            escaped = True
            continue
            
        if char == '"':
            if current_token and not in_string:
                tokens.append(''.join(current_token))
                current_token = []
            in_string = not in_string
            continue
            
        if in_string:
            # Skip content inside strings
            continue
            
        if char in ' ()\n\t':
            if current_token:
                tokens.append(''.join(current_token))
                current_token = []
        else:
            current_token.append(char)
    
    if current_token:
        tokens.append(''.join(current_token))
    
    return tokens

# Helper function to quote symbols while preserving string content
def quote_symbols_outside_strings(text, symbols_to_quote):
    """Quote symbols in text, but only outside of string literals."""
    result = []
    current_token = []
    in_string = False
    escaped = False
    
    i = 0
    while i < len(text):
        char = text[i]
        
        if escaped:
            result.append(char)
            escaped = False
            i += 1
            continue
            
        if char == '\\' and in_string:
            result.append(char)
            escaped = True
            i += 1
            continue
            
        if char == '"':
            # Flush current token if any
            if current_token:
                token = ''.join(current_token)
                if token in symbols_to_quote and not in_string:
                    result.append("'" + token)
                else:
                    result.append(token)
                current_token = []
            result.append(char)
            in_string = not in_string
            i += 1
            continue
            
        if in_string:
            # Inside string, just copy characters
            result.append(char)
            i += 1
            continue
            
        if char in ' ()\n\t':
            # Delimiter found, flush current token
            if current_token:
                token = ''.join(current_token)
                if token in symbols_to_quote:
                    result.append("'" + token)
                else:
                    result.append(token)
                current_token = []
            result.append(char)
            i += 1
        else:
            # Build up current token
            current_token.append(char)
            i += 1
    
    # Flush any remaining token
    if current_token:
        token = ''.join(current_token)
        if token in symbols_to_quote and not in_string:
            result.append("'" + token)
        else:
            result.append(token)
    
    return ''.join(result)

usercode_nocomments = "\n".join([remove_comments_preserve_strings(line) for line in usercode.split("\n")])

#2. Starting from a list of builtin functions we automatically add the defined MeTTa and Scheme functions&macros:
functions = set(["-", "+", "*", "/",        #arithmetic functions
                 "and", "or", "not",        #logical functions
                 "min", "max", "abs",       #math functions
                 "<", ">", "<=", ">=", "equal?"])     #comparison functions
for line in allcode.split("\n"):
    names = []
    if line.startswith("(=deterministic ("): #MeTTa functions
        names = [line.split("(=deterministic (")[1].split(" ")[0].split(")")[0]]
    if line.startswith("(=memoized ("): #MeTTa functions
        names = [line.split("(=memoized (")[1].split(" ")[0].split(")")[0]]
    if line.startswith("(= ("): #MeTTa functions
        names = [line.split("(= (")[1].split(" ")[0].split(")")[0]]
    elif line.startswith("(define "): #Scheme definitions
        rest = line.split("(define ")[1].strip()
        if rest.startswith("("): #function definition
            names = [rest.split("(")[1].split(" ")[0].split(")")[0]]
        else: #basic definition
            names = [rest.split(" ")[0]]
    elif line.startswith("(define-syntax "): #Scheme macros
        names = [line.split("(define-syntax ")[1].strip()]
    elif "(syntax-rules (" in line: #Scheme macro keywords
        names = line.split("(syntax-rules (")[1].split(")")[0].split(" ")
    elif "(foreign-safe-lambda" in line and "(define" in line:
        names=[line.split("(define ")[1].split("(foreign-safe-lambda")[0].strip()]
    for name in names:
        if name:
            functions.add(name)

#3. We now check for yet unquoted symbols (using proper string-aware tokenization):
tokens = extract_tokens_outside_strings(usercode_nocomments)
identified_symbols = set([x for x in tokens
                          if x != "" and x[0] != "$" #not a variable
                                     and not x in functions #not a function or macro
                                     and not x.replace("-","").replace(".","").isnumeric() #not a number
                                     and x != "#f" and x != "#t" #not a boolean
                                     and x[0] != '"']) #not a string

#4. We quote the identified symbols in the user code (string-aware):
newcode = quote_symbols_outside_strings(usercode, identified_symbols)

#5. Additionally, we remove quotes in type definitions, which is easier than keeping track of all defined types:
newcodefinal = ""
for line in newcode.split("\n"):
    if line.startswith("(Typedef "):
       line = line.replace("'", "")
    newcodefinal += line + "\n"

#6. Now, override the file with the one which has the properly quoted symbols
with open("RUN.scm", "w") as file:
    file.write(basecode + "\n;__METTACODE__:" + newcodefinal.replace("''","'"))
