package com.sigmacoders.aichildmonitor.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.sigmacoders.aichildmonitor.R
import com.sigmacoders.aichildmonitor.model.Child

class ChildrenAdapter(
    private val children: List<Child>,
    private val onClick: (Child) -> Unit
) : RecyclerView.Adapter<ChildrenAdapter.ViewHolder>() {

    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val childNameTextView: TextView = itemView.findViewById(R.id.childNameTextView)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_child, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val child = children[position]
        holder.childNameTextView.text = child.name
        holder.itemView.setOnClickListener { onClick(child) }
    }

    override fun getItemCount() = children.size
}