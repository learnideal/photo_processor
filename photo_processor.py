#!/usr/bin/python
from __future__ import print_function

import exifread
import filecmp
import getopt
import logging
import os
import re
import shutil
import sys
import time

kWorkingDirectory = 'scratch'

# Class for renaming photos based on their dates taken. Output None if no
# information can be found.
class FileRenamer(object):
    def __init__(self):
        self.date_time_key_list = ['EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 
            'Image DateTimeOriginal', 'Image DateTime'] 

    def ParseDateTime(self, date_time_string):
        try:
            date_time = time.strptime(date_time_string, '%Y:%m:%d %H:%M:%S')
            return time.strftime('%Y-%m-%d-%H.%M.%S', date_time)
        except ValueError:
            return None

    def Rename(self, photo_name):
        photo= open(photo_name, 'rb')
        exif_tags = exifread.process_file(photo)

        for date_time_key in self.date_time_key_list:
            if date_time_key in exif_tags.keys():
                date_time_value = '%s' % exif_tags[date_time_key]
                new_photo_file_name = self.ParseDateTime(date_time_value)
                if new_photo_file_name:
                    return new_photo_file_name
        return None

# Class for organizing photos in a specified folder by source and rename them
# in the same folder.  
class PhotoOrganizer(object):
    def __init__(self, source, destination):
        self.source = source
        self.file_renamer = FileRenamer()
        self.updated_photos = dict()
        self.destination = destination
        print('Output folder: ' + self.destination)

    def ParsePhotos(self, directory):
        print('Starting to parse photos in %s' % directory)
        processed_photo_count = 0
        new_timestamp_count = 0
        for file_name in os.listdir(directory):
            file_path = os.path.join(directory, file_name)
            if re.search('(jpg|JPG)$', file_name):
                new_file_name = self.file_renamer.Rename(file_path) or file_name[0:-4]
                if new_file_name in self.updated_photos.keys():
                    self.updated_photos[new_file_name].append(file_path)
                else:
                    self.updated_photos[new_file_name] = [file_path]
                    new_timestamp_count += 1
                processed_photo_count += 1
            print('Parsed %d photos.' % processed_photo_count, end='\r')
        print('Parsing in folder %s is done.' % directory +  
              '%d new time stamps were found,' % new_timestamp_count +
              '%d photos were processed.' % processed_photo_count)
    
    def DoClean(self, key):
        photo_file_name_list = self.updated_photos[key]
        is_redundant = [False for photo in photo_file_name_list]
        for candidate in range(1, len(photo_file_name_list)):
            for base in range(0, candidate):
                if not is_redundant[base] and filecmp.cmp(photo_file_name_list[base],
                    photo_file_name_list[candidate]):
                    is_redundant[candidate] = True
                    break
        unique_photos = [photo_file_name_list[i] for i in 
            range(0, len(photo_file_name_list)) if not is_redundant[i]]
        redundant_photos = [photo_file_name_list[i] for i in 
            range(0, len(photo_file_name_list)) if is_redundant[i]]
        if len(unique_photos) == 1:
            shutil.move(unique_photos[0], os.path.join(self.destination, key + '.jpg'))
        else:
            for i in range(0, len(unique_photos)):
                shutil.move(unique_photos[i], 
                            os.path.join(self.destination, key + '_%d.jpg' % i))
        if redundant_photos:
            logging.info('The following files are redundant: %s' % redundant_photos)
        
        if len(redundant_photos) == 1:
            shutil.move(redundant_photos[0], os.path.join(self.destination, key + '_dup.jpg'))
        elif len(redundant_photos) > 1:
            for i in range(0, len(redundant_photos)):
                shutil.move(redundant_photos[i], 
                            os.path.join(self.destination, key + '_dup_%d.jpg' % i))

    def DoOrganize(self):
        for root, dirs, files in os.walk(self.source):
            if (len(files) > 0):
                self.ParsePhotos(root)
        print('All parsing done. Now clean photos.')
        for key in self.updated_photos.keys():
            self.DoClean(key)
        print('All done.')

class PhotoOrganizerManager(object):
    def __init__(self, source):
        self.source = source

    def Run(self):
        PhotoOrganizer(self.source, self.source).DoOrganize()

if __name__ == '__main__':
    logging.basicConfig(filename='organizer.log', level=logging.INFO)
    source_dir = './'
    opts, args = getopt.getopt(sys.argv[1:], 'i:')
    for opt, arg in opts:
        if opt == '-i':
            source_dir = arg
    if source_dir[-1] != '/':
        source_dir = source_dir + '/'

    PhotoOrganizerManager(source_dir).Run()
