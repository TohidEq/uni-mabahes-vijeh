# Fake News Detection

- Mabahes Vijeh, Tohid Eghdami
- 26 Dec 2024

# 1: Download Dataset

Go to [FakeNews-DataSet-Website-kaggle](https://www.kaggle.com/datasets/subho117/fake-news-detection-using-machine-learning) address and download `archive.zip`(41MB) and extract `News.csv`(111MB) in `fake-news-detection` folder.

# 2: Install Dependencies

Run a terminal and install these packages by `pip` like this:
If u got error in arch base systems you can add `--break-system-packages` at the end of every `pip` command. or use `yay -S python-(package name)` to install them.

```bash
pip install scikit-learn
pip install wordcloud
pip install nltk
pip install tqdm
pip install pandas
pip install seaborn
pip install matplotlib
```

## Compelete `NLTK` Installition

In your terminal open a python session by entring `python` command and run these commands to download some modules:

```python
import nltk

nltk.download('wordnet')
nltk.download('punkt')
nltk.download('stopwords')
```
You need to run this command once and then you can use nltk without errors in your python apps.


# 3: Importing Libraries and Datasets

The libraries used are : 

- Pandas: For importing the dataset.
- Seaborn/Matplotlib: For data visualization.


```python
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
```

Let’s import the downloaded dataset. 


```python
data = pd.read_csv('News.csv',index_col=0)
data.head()
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>title</th>
      <th>text</th>
      <th>subject</th>
      <th>date</th>
      <th>class</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Donald Trump Sends Out Embarrassing New Year’...</td>
      <td>Donald Trump just couldn t wish all Americans ...</td>
      <td>News</td>
      <td>December 31, 2017</td>
      <td>0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Drunk Bragging Trump Staffer Started Russian ...</td>
      <td>House Intelligence Committee Chairman Devin Nu...</td>
      <td>News</td>
      <td>December 31, 2017</td>
      <td>0</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Sheriff David Clarke Becomes An Internet Joke...</td>
      <td>On Friday, it was revealed that former Milwauk...</td>
      <td>News</td>
      <td>December 30, 2017</td>
      <td>0</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Trump Is So Obsessed He Even Has Obama’s Name...</td>
      <td>On Christmas day, Donald Trump announced that ...</td>
      <td>News</td>
      <td>December 29, 2017</td>
      <td>0</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Pope Francis Just Called Out Donald Trump Dur...</td>
      <td>Pope Francis used his annual Christmas Day mes...</td>
      <td>News</td>
      <td>December 25, 2017</td>
      <td>0</td>
    </tr>
  </tbody>
</table>
</div>




- We can see shape of our dataset that means we have `44919` records that each record(or row) has `5` fields(or columns :`title`	`text`	`subject`	`date`	`class`})



```python
data.shape
```




    (44919, 5)




## Remove Unusable Fields in Dataset 
There is no need to `title`, `subject` and `date` columns, so we can drop them:



```python
data = data.drop(["title", "subject","date"], axis = 1)
```

Check if there is any null value to drop them:


```python
data.isnull().sum()
```




    text     0
    class    0
    dtype: int64




- OK, no null values. 

Now we have to shuffle the dataset to prevent the model to get bias. After that we will reset the index and then drop it. Because index column is not useful to us.



```python
# Shuffling
data = data.sample(frac=1)
data.reset_index(inplace=True)
# drop index column
data.drop(["index"], axis=1, inplace=True)
```


Now Let’s explore the unique values in the each category using below code.



```python
sns.countplot(data=data,
			x='class',
			order=data['class'].value_counts().index)
```




    <Axes: xlabel='class', ylabel='count'>




    
![png](output_14_1.png)
    



# 4: Preprocessing and analysis of News column

Firstly we will remove all the stopwords, punctuations and any irrelevant spaces from the text. For that `NLTK` Library is required and some of it’s module need to be downloaded. So, for that run the below code.

- I commented `nltk.download()` lines because i have downloaded them in `# 1: Download Dataset` section, if you skipped that section you can uncomment these lines to download modules



```python
from tqdm import tqdm
import re
import nltk
#nltk.download('wordnet')
#nltk.download('punkt')
#nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem.porter import PorterStemmer
from wordcloud import WordCloud
```


Once we have all the required modules, we can create a function name preprocess text. This function will preprocess all the data given as input.



```python
def preprocess_text(text_data):
	preprocessed_text = []

	for sentence in tqdm(text_data):
		sentence = re.sub(r'[^\w\s]', '', sentence)
		preprocessed_text.append(' '.join(token.lower()
								for token in str(sentence).split()
								if token not in stopwords.words('english')))

	return preprocessed_text
```


To implement the function in all the news in the text column, run the below command.
It will takes a few minutes. (18:21 for me)


```python
preprocessed_review = preprocess_text(data['text'].values)
data['text'] = preprocessed_review
```

    
    00%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 44919/44919 [18:21<00:00, 40.80it/s]


Let’s visualize the WordCloud for fake and real news separately.

## Real News:



```python
# Real
consolidated = ' '.join(
	word for word in data['text'][data['class'] == 1].astype(str))

wordCloud = WordCloud(width=1600,
					height=800,
					random_state=21,
					max_font_size=110,
					collocations=False)

plt.figure(figsize=(15, 10))
plt.imshow(wordCloud.generate(consolidated), interpolation='bilinear')
plt.axis('off')
plt.show()
```


    
![png](output_22_0.png)
    



## Fake News:



```python
# Fake
consolidated = ' '.join(
	word for word in data['text'][data['class'] == 0].astype(str))

wordCloud = WordCloud(width=1600,
					height=800,
					random_state=21,
					max_font_size=110,
					collocations=False)

plt.figure(figsize=(15, 10))
plt.imshow(wordCloud.generate(consolidated), interpolation='bilinear')
plt.axis('off')
plt.show()
```


    
![png](output_24_0.png)
    


Now, Let’s plot the bargraph of the top 20 most frequent words.


```python
from sklearn.feature_extraction.text import CountVectorizer


def get_top_n_words(corpus, n=None):
	vec = CountVectorizer().fit(corpus)
	bag_of_words = vec.transform(corpus)
	sum_words = bag_of_words.sum(axis=0)
	words_freq = [(word, sum_words[0, idx])
				for word, idx in vec.vocabulary_.items()]
	words_freq = sorted(words_freq, key=lambda x: x[1],
						reverse=True)
	return words_freq[:n]


common_words = get_top_n_words(data['text'], 20)
df1 = pd.DataFrame(common_words, columns=['Review', 'count'])

df1.groupby('Review').sum()['count'].sort_values(ascending=False).plot(
	kind='bar',
	figsize=(10, 6),
	xlabel="Top Words",
	ylabel="Count",
	title="Bar Chart of Top Words Frequency"
)
```




    <Axes: title={'center': 'Bar Chart of Top Words Frequency'}, xlabel='Top Words', ylabel='Count'>




    
![png](output_26_1.png)
    



# 5: Converting text into Vectors

Before converting the data into vectors, split it into train and test.



```python
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.linear_model import LogisticRegression

x_train, x_test, y_train, y_test = train_test_split(data['text'],
													data['class'],
													test_size=0.25)
```


Now we can convert the training data into vectors using TfidfVectorizer.



```python
from sklearn.feature_extraction.text import TfidfVectorizer

vectorization = TfidfVectorizer()
x_train = vectorization.fit_transform(x_train)
x_test = vectorization.transform(x_test)
```


# 6: Modet Training, Evaluation, and Prediction

Now, the dataset is ready to train the model

For training we will use `Logistic Regression` and evaluate the prediction accuracy using `accuracy_score`.

## Logistic Regression



```python
from sklearn.linear_model import LogisticRegression

model_L = LogisticRegression()
model_L.fit(x_train, y_train)

# testing the model
print(accuracy_score(y_train, model_L.predict(x_train)))
print(accuracy_score(y_test, model_L.predict(x_test)))
```

    0.9941227106770756
    0.9883348174532502


## Decision Tree Classifier



```python
from sklearn.tree import DecisionTreeClassifier

model_D = DecisionTreeClassifier()
model_D.fit(x_train, y_train)

# testing the model
print(accuracy_score(y_train, model_D.predict(x_train)))
print(accuracy_score(y_test, model_D.predict(x_test)))
```

    1.0
    0.9969723953695458



As we can see, `Decision Tree Classifier` has a little bit more accuracy score.

## Show confusion matrix for Logistic Regression:


```python
# Confusion matrix of Results from Logistic Regression
from sklearn import metrics
cm = metrics.confusion_matrix(y_test, model_L.predict(x_test))

cm_display = metrics.ConfusionMatrixDisplay(confusion_matrix=cm,
											display_labels=[False, True])

cm_display.plot()
plt.show()
```


    
![png](output_36_0.png)
    



## Show confusion matrix for Decision Tree Classifier:


```python
# Confusion matrix of Results from Decision Tree classification
from sklearn import metrics
cm = metrics.confusion_matrix(y_test, model_D.predict(x_test))

cm_display = metrics.ConfusionMatrixDisplay(confusion_matrix=cm,
											display_labels=[False, True])

cm_display.plot()
plt.show()
```


    
![png](output_38_0.png)
    

