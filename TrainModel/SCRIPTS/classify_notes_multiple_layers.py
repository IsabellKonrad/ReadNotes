import tensorflow as tf
import numpy as np
import scipy.misc
import csv
import os
import sys
import glob
import random
from PIL import Image

def get_min_samples(folders):
    min_samples = float('inf')
    for folder in folders:
        x = len(glob.glob(folder + '/*.jpg'))
        if x < min_samples:
            min_samples = x
    return min_samples


def get_Note_files_list(this_folder, equal):
    train_size = 0.99
    folder_list = sorted([x[0] for x in os.walk(this_folder)])[1:]
    folders1 = [folder for folder in folder_list if len(folder.split('/'))<3]
    min_samples = get_min_samples(folders1)

    files = []
    for folder1 in folders1:
        if equal == 'equal=True':
            files_equal = []
            folders2 = sorted([x[0] for x in os.walk(folder1)])
            for folder2 in folders2:
                files_equal = files_equal + glob.glob(folder2 + '/*.jpg')
            files = files + files_equal[:min_samples]
        else:
            folders2 = sorted([x[0] for x in os.walk(folder1)])
            for folder2 in folders2:
                files = files + glob.glob(folder2 + '/*.jpg')
    files = random.sample(files, len(files))
    files = random.sample(files, len(files))

    m_train = int(len(files)*train_size)
    return files[:m_train], files[m_train:]


def make_batches(files_list):
    batch_size = 50
    m = len(files_list)
    how_many = int(m/batch_size)
    Files_batches = []
    begin = 0
    for i in range(how_many):
        end = (i+1)*batch_size
        Files_batches.append(files_list[begin:end])
        begin = end
    if m - begin > 0:
        Files_batches.append(files_list[begin:m])
    return Files_batches
    

def make_XY(batch, size_X, FILES_FOLDER):
    X = np.zeros(shape=(0, size_X))

    Y_list = sorted(os.listdir(FILES_FOLDER))
    size_Y = len(Y_list)

    Y = np.zeros(shape=(0, size_Y))
    for file_name in batch:
        content = np.asarray(Image.open(file_name))
        next_row = np.reshape(content,(1,content.shape[0]*content.shape[1]))/255
        X = np.append(X,next_row,axis=0)
        i=0
        for Y_name in Y_list:
            if '/'+Y_name+'/' in file_name:
                next_row = np.eye(size_Y, dtype=int)[i,:]
                next_row = np.reshape(next_row,(1,size_Y))
                Y = np.append(Y, next_row, axis=0)
            i=i+1
        #print Y_list[list(next_row[0]).index(1)]
    return X, Y


def get_X_size(file_name):
    content = np.asarray(Image.open(file_name))
    size_X = content.shape[0]*content.shape[1]
    return size_X


def get_Y_size(FILES_FOLDER):
    size_Y = len(os.listdir(FILES_FOLDER))
    return size_Y


def classifier(FILES_FOLDER, equal):
    Files_list_train, Files_list_test = get_Note_files_list(FILES_FOLDER, equal)
    Files_batches = make_batches(Files_list_train)
    size_X = get_X_size(Files_list_test[0])
    size_Y = get_Y_size(FILES_FOLDER)

    def weight_variable(shape, this_name):
        initial = tf.truncated_normal(shape, stddev=0.1)
        return tf.Variable(initial, name=this_name)

    def bias_variable(shape, this_name):
        initial = tf.constant(0.1, shape=shape)
        return tf.Variable(initial, name=this_name)

    def conv2d(x, W):
        return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')

    def max_pool_2x2(x):
        return tf.nn.max_pool(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

    W_conv1 = weight_variable([11, 11, 1, 10], 'W_conv1')
    b_conv1 = bias_variable([10], 'b_conv1')
    x = tf.placeholder(tf.float32, [None, size_X])
    y_ = tf.placeholder(tf.float32, [None, size_Y])
    x_image = tf.reshape(x, [-1,32,80,1])    

    h_conv1 = tf.nn.relu(conv2d(x_image, W_conv1) + b_conv1)
    h_pool1 = max_pool_2x2(h_conv1)

    #W_conv2 = weight_variable([7, 7, 32, 64], 'W_conv2')
    #b_conv2 = bias_variable([64], 'b_conv2')

    #h_conv2 = tf.nn.relu(conv2d(h_pool1, W_conv2) + b_conv2)
    #h_pool2 = max_pool_2x2(h_conv2)

    W_fc1 = weight_variable([80/2 * 32/2 * 10, 10], 'W_fc1')    #W_conv2, b_conv2, h_conv2, h_pool2 rausgelassen, fc1 64 -> 32
    b_fc1 = bias_variable([10], 'b_fc1')

    h_pool2_flat = tf.reshape(h_pool1, [-1, 80/2 * 32/2 * 10])
    h_fc1 = tf.nn.relu(tf.matmul(h_pool2_flat, W_fc1) + b_fc1)

    keep_prob = tf.placeholder("float")
    h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob)

    W_fc2 = weight_variable([10, size_Y], 'W_fc2')
    b_fc2 = bias_variable([size_Y], 'b_fc2')

    y_conv=tf.nn.softmax(tf.matmul(h_fc1_drop, W_fc2) + b_fc2)

    cross_entropy = -tf.reduce_sum(y_*tf.log(y_conv + 1e-10))
    train_step = tf.train.AdamOptimizer(1e-4).minimize(cross_entropy)
    correct_prediction = tf.equal(tf.argmax(y_conv,1), tf.argmax(y_,1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, "float"))
    saver = tf.train.Saver()

    print '\n\nSecond Model \n'

    sess = tf.Session()
    sess.run(tf.initialize_all_variables())

    #saver.restore(sess, "../MODEL/model_layers.ckpt")
    #print("Model restored.")

    i=0
    for batch in Files_batches[:500]:
        X_train, Y_train = make_XY(batch, size_X, FILES_FOLDER)
        if i%10 == 0:
            train_accuracy = accuracy.eval(session=sess, feed_dict={x: X_train, y_: Y_train, keep_prob: 1.0})
            print('Training accuracy %g' % train_accuracy)
        train_step.run(session = sess, feed_dict={x: X_train, y_: Y_train, keep_prob: 0.5})
        i=i+1

    X_test, Y_test = make_XY(Files_list_test, size_X, FILES_FOLDER)
    print("Test accuracy %g"%accuracy.eval(session = sess, feed_dict={x: X_test, y_: Y_test, keep_prob: 1.0}))
    prediction=tf.argmax(y_conv,1)
    result = prediction.eval(session = sess, feed_dict={x: X_test, keep_prob: 1.0})
    #result = sess.run(y_conv, feed_dict={x: X_test, keep_prob: 1.0})

    Y_list = sorted(os.listdir(FILES_FOLDER))
    Rf = open('result.txt','w')
    for xx,yy in zip(Files_list_test, result):
        yyy = Y_list[yy]
        to_save = xx + ' ' + yyy + '\n'
        Rf.write(to_save)
    Rf.close()

    if not os.path.exists('../MODEL/'):
        os.makedirs('../MODEL/')

    #save_path = saver.save(sess, "../MODEL/model_layers.ckpt")
    save_path = saver.save(sess, "../MODEL/model_layers_yes.ckpt")
    print('Model saved in file: %s' % save_path)





    #probabilities=y_conv
    #print "probabilities", probabilities.eval(feed_dict={x: X_test, keep_prob:1.0}, session=sess)


if __name__ == '__main__':
    FILES_FOLDER = sys.argv[1]
    equal = sys.argv[2]
    classifier(FILES_FOLDER, equal)