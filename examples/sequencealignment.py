# Create sequences to be aligned.
from alignment.sequence import Sequence
a = Sequence("what a beautiful day".split())
b = Sequence("what a disappointingly bad day".split())
print "Sequence A:", a
print "Sequence B:", b
print

# Create a vocabulary and encode the sequences.
from alignment.vocabulary import Vocabulary
v = Vocabulary()
aEncoded = v.encodeSequence(a)
bEncoded = v.encodeSequence(b)
print "Encoded A:", aEncoded
print "Encoded B:", bEncoded
print

# Create a scoring and align the sequences using global aligner.
from alignment.sequencealigner import SimpleScoring, GlobalSequenceAligner
scoring = SimpleScoring(2, -1)
aligner = GlobalSequenceAligner(scoring, -2)
score, encodeds = aligner.align(aEncoded, bEncoded, backtrace=True)

# Iterate over optimal alignments and print them.
for encoded in encodeds:
	alignment = v.decodeSequenceAlignment(encoded)
	print alignment
	print "Alignment score:", alignment.score
	print "Percent identity:", alignment.percentIdentity()
	print
