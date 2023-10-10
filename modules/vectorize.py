#Semantic Text Segmentation Prior to Generating Text Embeddings 
import spacy
from typing import List
import pdfplumber


from PyPDF2 import PdfReader

def extract_text_from_pdf(file):
    pdf = PdfReader(file)
    text = ""
    pages = len(pdf.pages)
    print("Extracting text from PDF...")
    for i in range(pages):
        page = pdf.pages[i]
        text += page.extract_text()
        if i % 10 == 0 or i == pages-1:  # print every 10 pages or when it's done
            print(f"Progress: {i}/{pages-1}")
    return text
    
def remove_stop_words(text: str,nlp) -> str:
  doc = nlp(text)
  total_tokens = len(doc)
  text_parts = []
  print("Removing stop words...")
  for i, token in enumerate(doc, start=1):
    if not token.is_stop:
      text_parts.append(token.text)
      print(token.text)
    if i % 1000 == 0 or i == total_tokens:  # print every 100 tokens or when it's done
      print(f"Progress: {i}/{total_tokens}")
  return " ".join(text_parts)

def split_sentences(text: str,nlp) -> List[str]:
  doc = nlp(text)
  total_sents = len(list(doc.sents))
  sentences = []
  print("Splitting into sentences...")
  for i, sent in enumerate(doc.sents, start=1):
    sentences.append(sent.text)
    if i % 1000 == 0 or i == total_sents:  # print every 10 sentences or when it's done
      print(f" Splitting Progress: {i}/{total_sents}")
  return sentences

def group_sentences_semantically(sentences: List[str], threshold: int,nlp) -> List[str]:
  docs = [nlp(sentence) for sentence in sentences]
  segments = []

  start_idx = 0
  end_idx = 1
  segment = [sentences[start_idx]]
  print("Grouping sentences semantically...")
  while end_idx < len(docs):
    if docs[start_idx].similarity(docs[end_idx]) >= threshold:
      segment.append(sentences[end_idx])  # Here we append the sentence text, not the Doc object
      print(segment)
    else:
      segments.append(" ".join(segment))
      start_idx = end_idx
      segment = [sentences[start_idx]]
            
    end_idx += 1

  if segment:
    segments.append(" ".join(segment))

  return segments


def split_text_into_segments(text: str,language: str) -> List[str]:
  
  if language == "en":
    nlp = spacy.load("en_core_web_sm")
  elif language == "es":
    nlp = spacy.load("es_dep_news_trf")

  # text_no_stop_words = remove_stop_words(text,nlp)
  # print(len(text_no_stop_words))
  sentences = split_sentences(text,nlp)
  print('sentences: ',len(sentences))
  return group_sentences_semantically(sentences, 0.6,nlp)


import pandas as pd
import os

# get the pdf file in the directory and convert it to text
file = 'Mediación Cultural en Museos.pdf'
text = extract_text_from_pdf(file)
# split the text into segments
segments = split_text_into_segments(text,'es')
# save the segments into a csv file
df = pd.DataFrame(segments)
df.to_csv('Mediación Cultural en Museos.csv',index=False,header=False)
