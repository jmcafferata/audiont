
def clean_options(response):
    options = []
    # find option 1. (ending in new line) and add it to the options list // encontrar opción 1. y agregarla a la lista de opciones
    options.append(response.split("1.")[1].split("\\n")[0])
    options.append(response.split("2.")[1].split("\\n")[0])
    options.append(response.split("3.")[1].split("\\n")[0])
    options.append(response.split("4.")[1].split("\\n")[0])

    
    # delete the numbers from the options // eliminar los números de las opciones
    options[0] = options[0].replace("\\n", "")
    options[1] = options[1].replace("\\n", "")
    options[2] = options[2].replace("\\n", "")
    options[3] = options[3].replace("\\n", "")
    print("Option 3: "+ options[3])
    # delete the opening and closing brackets from the options // eliminar los corchetes de apertura y cierre de las opciones
    options[0] = options[0].replace("[", "")
    options[1] = options[1].replace("[", "")
    options[2] = options[2].replace("[", "")
    options[3] = options[3].replace("[", "")
    options[0] = options[0].replace("]", "")
    options[1] = options[1].replace("]", "")
    options[2] = options[2].replace("]", "")
    options[3] = options[3].replace("]", "")
    print("Option 3: "+ options[3])
    # delete the quotes from the options // eliminar las comillas de las opciones
    options[0] = options[0].replace("'", "")
    options[1] = options[1].replace("'", "")
    options[2] = options[2].replace("'", "")
    options[3] = options[3].replace("'", "")
    print("Option 3: "+ options[3])

    print(options[3])
    # delete everything that comes after \n 1. // eliminar todo lo que viene después de \n 1.
    response_text = response.split("1.")[0]
    print(response_text)
    return response_text, options

response = "El remitente te propone usar distintas formas para los engranajes para mostrar algo más dinámico y te está planteando varias secuencias.\n\nOpciones de respuesta:\n1. Estoy de acuerdo.\n2. No estoy de acuerdo.\n3. No tengo preferencia.\n4. Otra respuesta."
clean_options(response)