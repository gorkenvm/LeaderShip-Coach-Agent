from langchain.document_loaders import LocalFileSystemLoader
from langchain.prompts import PromptTemplate
from langchain.llm import OpenAI
from langchain.extractors import QuestionAnswerExtractor
from langchain.chains.question_answering import extract_qa_pairs

# Prompt template for extracting questions and answers
prompt_template = PromptTemplate(
    input_variables=["transcript"],
    template="""
        Aşağıda Tecrübe Konuşuyor adlı TV programının bölümlerinin transkriptler verilmiştir. Liderler bu programda tecrübeleri ile ilgili sorulara yanıt vermektedir. Lütfen bu transkriten soruları ve yanıtlarını çıkarın.
        Soru ve cevapları, LLM tune ve RAG sisteminde kullanmak üzere ayrı ayrı dosyalara kaydedin.
        Transcript:
        {transcript}
        
        Sorular:
    """
)

# Set up the LLM
llm = OpenAI(api_key="your_api_key")  # Unutmayın, OpenAI API anahtarınızı buraya eklemelisiniz

# Define the directory with the transcript .txt files
transcript_dir = "path/to/your/transcripts"  # Transkript dosyalarının bulunduğu dizin

# Load the transcript files
loader = LocalFileSystemLoader(file_paths=[f"{transcript_dir}/{filename}" for filename in os.listdir(transcript_dir) if filename.endswith('.txt')])

# Extract questions and answers
extractor = QuestionAnswerExtractor(llm=llm, prompt_template=prompt_template)

# Iterate over each transcript to extract Q&A pairs
for document in loader.load():
    transcript = document.content
    qa_pairs = extract_qa_pairs(llm, transcript, prompt_template)
    
    # Save the extracted questions and answers
    with open(f"{transcript_dir}/extracted_qa_{document.metadata['filename']}.txt", 'w') as f:
        for question, answer in qa_pairs:
            f.write(f"Soru: {question}\nCevap: {answer}\n\n")

print("Soru ve cevaplar başarıyla çıkarıldı ve kaydedildi.")