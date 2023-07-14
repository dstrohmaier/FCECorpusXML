import argparse
import utils
from pathlib import Path

from FCECorpusHandler import FCECorpusHandler


""" Module to parse XML in Python using minidom"""


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extracts transcript and summary from FCE Corpus.')
    parser.add_argument('--fce_xml_dir', type=Path, default=utils.project_dir_name() + '/data/',
                        help='FCE Corpus download directory')
    parser.add_argument('--results_dir', type=Path,
                        default=utils.project_dir_name() + '/data/fce_txt/',
                        help='FCE Corpus txt format')
    parser.add_argument('--selected_langs', nargs='*', default=['spanish', 'german', 'japanese'],
                        help='L1 selection')
    args = parser.parse_args()

    fceCorpusHandler = FCECorpusHandler(args)

    fceCorpusHandler.get_train_dev_test_sets()

    fceCorpusHandler.xml_to_txt(data_type="train")
    fceCorpusHandler.xml_to_txt(data_type="dev")
    fceCorpusHandler.xml_to_txt(data_type="test")
