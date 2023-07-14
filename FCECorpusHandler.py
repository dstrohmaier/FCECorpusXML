import utils
import os
import csv
import urllib.request
import zipfile
import tarfile
import shutil

from xml.dom import minidom

__author__ = "Gwena Cunha, David Strohmaier"

"""
- Downloads dataset
- Extracts information from XML (original and corrected essays)
- Saves as txt files: target, source, vocab
"""


class FCECorpusHandler:
    def __init__(self, args):
        self.args = args

        self.selected_langs = args.selected_langs

        self.results_dir = args.results_dir
        utils.ensure_dir(self.results_dir)

        self.fce_xml_dir = self.args.fce_xml_dir
        print(f"Create data directory: {self.fce_xml_dir}")
        self.fce_xml_dir.mkdir(parents=True, exist_ok=True)

        self.fce_error_detection_dir = self.args.fce_xml_dir / 'fce-error-detection'
        self.download_fce_error_detection_corpus()

        self.fce_dir = self.args.fce_xml_dir / 'fce-released-dataset'
        self.download_fce_corpus()

    def download_fce_error_detection_corpus(self):
        """ Check if FCE Error Detection Corpus exists and only download it if it doesn't

        :return: directory where FCE Error Detection Corpus is located
        """
        download_link = 'https://s3-eu-west-1.amazonaws.com/ilexir-website-media/fce-error-detection.tar.gz'
        if not os.path.exists(self.fce_error_detection_dir):
            print("Downloading FCE Error Detection Corpus")
            targz_fce_filename = self.fce_error_detection_dir.stem + '.tar.gz'
            # Download file
            urllib.request.urlretrieve(download_link, targz_fce_filename)

            # Untar compressed file
            tar = tarfile.open(targz_fce_filename)
            tar.extractall(self.fce_xml_dir)
            tar.close()

            # Delete .tar.gz file
            os.remove(targz_fce_filename)
        else:
            print("FCE Error Detection Corpus has already been downloaded in: {}".format(self.fce_error_detection_dir))

    def download_fce_corpus(self):
        """ Check if FCE Corpus exists and only download it if it doesn't

        :return: directory where FCE Corpus is located
        """
        download_link = 'https://s3-eu-west-1.amazonaws.com/ilexir-website-media/fce-released-dataset.zip'
        if not os.path.exists(self.fce_dir):
            print("Downloading FCE Corpus")
            zip_fce_filename = self.fce_dir.stem + '.zip'
            # Download file
            urllib.request.urlretrieve(download_link, zip_fce_filename)

            # Unzip compressed file
            zip_ref = zipfile.ZipFile(zip_fce_filename, 'r')
            zip_ref.extractall(self.fce_xml_dir)
            zip_ref.close()

            # Delete .tar.gz file
            os.remove(zip_fce_filename)
        else:
            print("FCE Corpus has already been downloaded in: {}".format(self.fce_dir))

    def get_train_dev_test_sets(self):
        print("\nGet train-dev-test sets")

        # Copy all files from "fce-released-dataset/dataset/*" to "fce-released-dataset/dataset_all/"
        fce_dir_dataset = self.fce_dir / 'dataset'
        fce_dir_save = self.fce_dir / 'dataset_all'
        fce_dir_save.mkdir(parents=True, exist_ok=True)

        for f_path in fce_dir_dataset.glob('**/*.xml'):
            shutil.copy2(f_path, fce_dir_save)

        # Separate train, dev, test
        train_dev_test_path = self.fce_error_detection_dir / 'filenames'
        for f_path in train_dev_test_path.glob('*.txt'):
            set_dir = self.fce_dir / f_path.stem.split('.')[1]
            set_dir.mkdir(parents=True, exist_ok=True)

            with open(f_path, 'r') as read_file:
                f_lines = read_file.read().split('\n')

            for l in f_lines:
                if len(l) > 0:
                    shutil.copy2(fce_dir_save / l, set_dir)

    def xml_to_txt(self, data_type='train', verbose=False):
        print("\nGet train-dev-test sets")
        fce_dir_dataset = self.fce_dir / data_type
        fce_txt_dir_dataset = self.results_dir / data_type

        # Save in results_dir, split into sub_dir for original and corrected
        # Task: generate incorrect sentences from correct ones, thus source is incorrect and target is correct
        print(f'fce_txt_dir_dataset: {fce_txt_dir_dataset}')
        print(f'fce_dir_dataset: {fce_dir_dataset}')

        writers = {}
        files = []
        for lang in self.selected_langs:
            tsv_file = open(f'{lang}_{data_type}_l1.tsv', 'w', encoding='utf-8')
            files.append(tsv_file)
            field_names = ['Text', 'Essay']
            writer = csv.DictWriter(tsv_file, fieldnames=field_names, delimiter='\t')
            writer.writeheader()
            writers[lang] = writer

        # Convert from xml to txt
        for f_path in fce_dir_dataset.glob('*.xml'):

            mydoc = minidom.parse(str(f_path))

            lang = mydoc.getElementsByTagName('language').item(0).firstChild.nodeValue
            lang = lang.lower()  # use lower case for languages

            print(lang)
            if lang not in self.selected_langs:
                continue

            items_essay = mydoc.getElementsByTagName('p')
            for item_essay in items_essay:
                incorrect_sent, _ = self.strip_str(item_essay, verbose=verbose)

                writers[lang].writerow({
                    'Text': incorrect_sent,
                    'Essay': f_path.stem
                })

        for f in files:
            f.close()
        print(f"Finished writing {data_type} files")

    def strip_str(self, item_essay, verbose=False):
        incorrect_sent = ''
        correct_sent = ''
        for child in item_essay.childNodes:
            if child.localName is None:  # no child nodes
                segment = child.data
                incorrect_sent += segment
                correct_sent += segment
                # print(segment)
            else:  # 'NS', 'i', 'c'
                inc_sent, cor_sent = self.recursive_NS_tag_strip(child)
                incorrect_sent += inc_sent
                correct_sent += cor_sent
        if verbose:
            print("Incorrect sentence: " + incorrect_sent)
            print("Correct sentence: " + correct_sent)
        return incorrect_sent, correct_sent

    def recursive_NS_tag_strip(self, item_ns):
        incorrect_sent = ''
        correct_sent = ''
        if item_ns.localName is None:  # base case
            segment = item_ns.data
            return segment, segment
        elif item_ns.localName == 'i':  # incorrect
            if item_ns.childNodes[0].localName is None:
                segment = item_ns.childNodes[0].data
                return segment, ''
            else:
                for child in item_ns.childNodes:
                    inc_sent, cor_sent = self.recursive_NS_tag_strip(child)
                    incorrect_sent += inc_sent
                    correct_sent += cor_sent
        elif item_ns.localName == 'c':  # correct
            if item_ns.childNodes[0].localName is None:
                segment = item_ns.childNodes[0].data
                return '', segment
            else:
                for child in item_ns.childNodes:
                    inc_sent, cor_sent = self.recursive_NS_tag_strip(child)
                    incorrect_sent += inc_sent
                    correct_sent += cor_sent
        else:  # NS
            for child in item_ns.childNodes:
                inc_sent, cor_sent = self.recursive_NS_tag_strip(child)
                incorrect_sent += inc_sent
                correct_sent += cor_sent
        return incorrect_sent, correct_sent

    def save_file(self, text, out_dir, filename):
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / filename, 'w') as out_file:
            out_file.write(text)
