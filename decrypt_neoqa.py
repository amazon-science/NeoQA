"""
Usage:
  decrypt_neoqa.py <src> <key>

Arguments:
  <src>   The source file to decrypt.
  <key>   The decryption key to use.
"""
import base64
import codecs
from os import makedirs, listdir
from os.path import join

from docopt import docopt


def xor_decrypt(encrypted_text: str, key: int) -> str:
    key = key % 256
    encrypted_bytes = base64.b64decode(encrypted_text)
    decrypted = ''.join(chr(b ^ key) for b in encrypted_bytes)
    return decrypted


def decrypt_neoqa(src: str, dest: str, key: int):
    makedirs(dest, exist_ok=True)
    for file in listdir(src):
        print('Decrypt:', file, '...', end=' ', flush=True)
        file_path = join(src, file)
        with codecs.open(file_path, encoding='utf-8') as f_in:
            with codecs.open(join(dest, file), 'w', encoding='utf-8') as f_out:
                for line in f_in.readlines():
                    f_out.write(xor_decrypt(line, key).strip() + '\n')
        print('(Done)', flush=True)


def main():
    # Parse command-line arguments using docopt
    arguments = docopt(__doc__)
    src = arguments['<src>']
    key = int(arguments['<key>'])

    # Decrypt the file using the provided arguments
    decrypt_neoqa(src, './dataset', key)


if __name__ == '__main__':
    main()
